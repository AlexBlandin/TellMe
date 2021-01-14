#!/usr/bin/env python3
import os
import json
import logging
import importlib
from time import time
from typing import List
from pathlib import Path
from math import isfinite
from datetime import datetime
from subprocess import run, PIPE
from random import sample, shuffle, seed

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import asyncio
import discord
import youtube_dl
from gtts import gTTS
from ulid import ULID
from parse import parse
from discord.ext import commands, tasks
from discord.ext.commands import Context
from discord import VoiceChannel, TextChannel, Role, Message, Reaction, Member, Guild

import speech_recognition as sr
# pip install -U SpeechRecognition

# Thanks to imayhaveborkedit's patches (semi-up to date by Gorialis) we have audio recording
# pip install -U "discord.py[voice] @ git+https://github.com/Gorialis/discord.py@voice-recv-mk3"

from extractor import Extractor

# permissions 53540928: send messages ... attach files, add reactions, connect, speak, move members, use voice activity

# refactor into `!play` command that triggers everything, TellMe cog is automated otherwise



# lib = next(Path("/").rglob("libopus.so*"))
lib = Path("/usr/lib/x86_64-linux-gnu/libopus.so.0.7.0")
discord.opus.load_opus(lib)
print(f"Audio working" if discord.opus.is_loaded() else "Uh oh", str(lib))

extractor = Extractor()

ulid = ULID()
logger = logging.getLogger("discord")
logger.setLevel(logging.INFO) # logging.WARNING # logging.ERROR
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)

recording_folder = Path("./audio/rec/")
recording_folder.mkdir(parents=True, exist_ok=True)

SFX=[f.name for f in Path("./audio/sfx/").glob("*")] # Some nice SFX to use (for "login" etc only right now)
"""
S: Up Chime 2 by FoolBoyMedia | License: Attribution
S: Flourish Spacey 1 by GameAudio | License: Creative Commons 0
S: gotItem.mp3 by Kastenfrosch | License: Creative Commons 0
"""

BGM=[f.name for f in Path("./audio/bgm/").glob("*")] # Some nice BGM to use
"""
S: Drone_DarkEmptiness.wav by ceich93 | License: Creative Commons 0
S: Low Slow Metal by be-steele | License: Creative Commons 0
S: abstract (ambient loop) by ShadyDave | License: Attribution Noncommercial
S: Mystical Cavern by Efecto Fundador | License: Attribution
S: Castle Music Loop #1 by Sirkoto51 | License: Attribution
S: River Stream (Subtle, slow, gentle) by CaganCelik | License: Creative Commons 0
S: Clock ticking.wav by ZoeVixen | License: Creative Commons 0
S: Ambient electronic loop 001 by frankum | License: Attribution
"""

shuffle(SFX)
shuffle(BGM)

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ""

ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "audio/temp/%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True, "noplaylist": True,
    "nocheckcertificate": True, "ignoreerrors": False,
    "logtostderr": False, "quiet": True, "no_warnings": True,
    "default_search": "auto", "source_address": "0.0.0.0"
}
ffmpeg_options = {
  "options": "-vn"
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
class YTDLSource(discord.PCMVolumeTransformer):
  def __init__(self, source, *, data, volume=0.5):
    super().__init__(source, volume)
    self.data = data
    self.title = data.get("title")
    self.url = data.get("url")

  @classmethod
  async def from_url(cls, url, *, loop=None, stream=False):
    loop = loop or asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
    if "entries" in data:
      # take first item from a playlist
      data = data["entries"][0]
    filename = data["url"] if stream else ytdl.prepare_filename(data)
    return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class TellMe(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.Vlobby, self.Vtalking = None, None # Voice Channels
    self.Tlobby, self.Tvoting = None, None # Text Channel
    self.Rcanvote, self.Rspeaking = None, None # Roles
    self.rounds, self.T = 1, 90
    seed(time())

  @commands.command()
  async def join(self, ctx: Context, *, channel: discord.VoiceChannel):
    """Joins a voice channel"""
    if ctx.voice_client is not None:
      await ctx.voice_client.move_to(channel)
    elif channel is not None:
      await channel.connect()
    else:
      await ctx.author.voice.channel.connect()
    await self.alert(ctx)
  
  @commands.command()
  async def volume(self, ctx: Context, volume: int):
    """Changes the player's volume"""

    if ctx.voice_client is None:
      return await ctx.send("Not connected to a voice channel.")
    ctx.voice_client.source.volume = volume / 100
    await ctx.send(f"Changed volume to {volume:.0%}")

  async def alert(self, ctx: Context):
    track = Path(f"./audio/sfx/{sample(SFX,1)[0]}")
    shuffle(SFX)
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track))
    ctx.voice_client.play(source, after=lambda e: print(f"Player error: {e}") if e else None)

  @commands.command()
  async def bgm(self, ctx: Context, *, query):
    """Plays from a local file or url (almost anything youtube_dl supports)"""
    if query in BGM or query.strip()=="":
      track = Path(f"./audio/bgm/{query if query in BGM else sample(BGM,1)[0]}")
      shuffle(BGM)
      source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track))
      ctx.voice_client.play(source, after=lambda e: print(f"Player error: {e}") if e else None)
      await ctx.send(f"Now playing: {query}")
    else:
      async with ctx.typing():
        player = await YTDLSource.from_url(query, loop=self.bot.loop)
        ctx.voice_client.play(player, after=lambda e: print(f"Player error: {e}") if e else None)

      await ctx.send(f"Now playing: {player.title}")

  @commands.command()
  async def say(self, ctx: Context, *, msg: str):
    if msg[:12] == "./audio/pre/":
      f = Path(msg) # pre-recorded
    else:
      f = Path(f"./audio/rec/r{ulid.generate()}.wav")
      f.touch(exist_ok=True)
      gTTS(msg).save(str(f))
    wait = float(json.loads(run(["ffprobe", "-i", str(f), "-loglevel", "quiet", "-print_format", "json", "-show_streams"], encoding="utf-8", stdout=PIPE).stdout)["streams"][0]["duration"]) + 0.5
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(f))
    ctx.voice_client.play(source, after=lambda e: print(f"Player error: {e}") if e else None)
    await asyncio.sleep(wait) # wait for speech to pass
    return f

  @commands.command()
  async def play(self, ctx: Context):
    """Plays TellMe"""
    """
    assume everyone is assembled in the "lobby" voice & text channel,
    one user (me) will type `!play`,
      specifies gamemode (for now, just controls number of rounds in a game) (not important for now)
        "basic" is 1 round per game
        "twoturn" is 2 rounds per game (not important for now)
    TellMe will connect to the author's location,
      query the channel for the list of users,
      clear any TellMe game roles ("canvote" & "speaking"),
      assign a random play order,
      announce the play order,
      move into the "speaking" voice & text channel
    gameloop begins (individual turns of all players forming a round),
      TellMe knows the k'th player,
      gives them the "speaking" role,
      moves them into the "speaking" channels,
      gives them the rundown:
        f"The last sentence was: {ls}" if k!=0 else f"Tell me a {genre} story set in {location} with {item}"
        f"Your prompt words are: {' '.join(prompts)}"
        f"You will have {T} seconds to tell me a story. When there are ten seconds remaining, an alert will play."
        f"Your {T} seconds starts, now."
      records for 90s (bgm optional),
        alert at 10s remaining,
      announces that time is up,
        assigns them the "canvote" role,
        invites them to move back to the lobby and look at the voting text channel to vote momentatily,
        forcefully moves them and removes "speaking" role,
      runs recording through extractor,
      puts keywords up for voting,
        message with reacts 1 through 10,
        alert those in lobby by text and voice that they have 20s to vote,
        wait 20s,
        tally votes,
        `prompts = ` top 4 (ties settled by random sample),
        thank those who voted and delete the vote message,
      loop,
    end of round,
      unassigns "canvote" role,
      (that's all for now), 
    end of game,
      report back the combined story,
        including TellMe's rundown and the votes
      upload stitched together audio (.opus in a .webm for discord embedding?),
      thank,
      cleanup,
        remove TellMe game roles,
    disconnect from voice.
    """
    dget, server = discord.utils.get, ctx.guild
    server: Guild
    vchannels, tchannels, roles = server.voice_channels, server.text_channels, server.roles
    self.Vlobby, self.Vtalking = dget(vchannels, name="Waiting Room"), dget(vchannels, name="Talking")
    self.Tlobby, self.Tvoting = ctx.channel, dget(tchannels, name="voting")
    self.Rcanvote, self.Rspeaking = dget(roles, name="TellMe-Voting"), dget(roles, name="TellMe-Speaking")
    self.Vlobby: VoiceChannel; self.Vtalking: VoiceChannel
    self.Tlobby: TextChannel; self.Tvoting: TextChannel
    self.Rcanvote: Role; self.Rspeaking: Role

    await self.say(ctx, msg="./audio/pre/welcome-to-tellme.wav")
    # await self.join(ctx, channel=None)
    vc = ctx.voice_client
    players = vc.channel.members
    players = [player for player in players if player.bot==False]
    shuffle(players)
    players: List[Member]
    for player in players:
      await player.remove_roles(self.Rspeaking, self.Rcanvote)
    print(),print(),print(),print()
    turn_order = f"The turn order is: {' then '.join([player.display_name for player in players])}"
    print(turn_order)
    print(),print(),print(),print()
    await ctx.send(turn_order)
    await self.say(ctx, msg=turn_order)
    await self.say(ctx, msg="./audio/pre/i-shall-begin-shortly.wav")
    await asyncio.sleep(0.5)
    await self.goto_talking(ctx)
    
    await asyncio.sleep(5) # wait to see if it moves
    
    genre, location, item = "Horror", "Swiss Mountains", "Goat"
    prompts, last = [], ""
    
    audio_files = [] # in order of occurence
    
    # Gameloop
    for r in range(min(1,self.rounds)):
      print(),print(),print(),print()
      print(f"Round {r}")
      print(),print(),print(),print()
      # Roundloop
      for i, player in enumerate(players):
        await self.bring_to_me(ctx, player)
        await player.add_roles(self.Rspeaking)
        await asyncio.sleep(5) # wait to see if it moves
        print(),print(),print(),print()
        print("Rundown")
        print(),print(),print(),print()
        if i == 0:
          s = await self.say(ctx, msg=f"Tell me a {genre} story set in {location} with {'' if item[-1]=='s' else 'an' if item[0] in 'aeiouh' else 'a'} {item}")
          audio_files.append(s)
        else:
          s = await self.say(ctx, msg=f"The last sentence was. {last}.")
          audio_files.append(s)
          print(),print(),print(),print()
          print("Prompts:")
          print(prompts)
          print(),print(),print(),print()
          s = await self.say(ctx, msg=f"Your prompt words are. {', '.join(prompts)}.")
          audio_files.append(s)
        print(),print(),print(),print()
        print("Get ready")
        print(),print(),print(),print()
        time = max(15,float(self.T))
        s = await self.say(ctx, msg=f"You will have {time} seconds to tell me a story. You should hear an alert when there are ten seconds remaining. Your {time} seconds starts, now.")
        audio_files.append(s)
        print(),print(),print(),print()
        print("Start")
        print(),print(),print(),print()
        # recording = await self.record(ctx, time=90)
        vc = ctx.voice_client
        recording = recording_folder / f"r{ulid.generate()}.wav"
        recording.touch(exist_ok=True)
        print(),print(),print(),print()
        print(f"Recording {time}s in {str(recording)}")
        print(),print(),print(),print()
        vc.listen(discord.WaveSink(str(recording)))
        await asyncio.sleep(time-10)
        await self.alert(ctx)
        await asyncio.sleep(10)
        # "Done" but not really, latency compensation so don't close yet
        s = await self.say(ctx, msg="./audio/pre/your-time-is-up.wav")
        if i != len(players)-1:
          await self.say(ctx, msg="./audio/pre/momentarily-you-will-be.wav")
        else:
          await self.say(ctx, msg="./audio/pre/the-round-has-ended.wav")
        await player.add_roles(self.Rcanvote)
        await asyncio.sleep(5)
        await self.move_back(ctx, player)
        # await asyncio.sleep(15) # latency adjustment (not necessary now we actually spend time talking?)
        vc.stop_listening()
        audio_files.append(recording)
        audio_files.append(s)
        await player.remove_roles(self.Rspeaking)
        print(),print(),print(),print()
        print(f"Recording complete {str(recording)}")
        print(),print(),print(),print()
        keywords, last = extractor.extract(str(recording))
        if i != len(players)-1:
          ping = await self.Tvoting.send("Please vote on the following prompts by selecting the corresponding number:")
          message = await self.Tvoting.send(" ".join([f"{i}. {p} " for i, p in enumerate(keywords,start=1)]))
          message: Message
          reactions = {}
          for k, (n, e) in zip(keywords, enumerate(["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"])):
            await message.add_reaction(e)
            await asyncio.sleep(0.5)
            reactions[e] = n
            print(k, n, e)
          await asyncio.sleep(20) # 20s voting period for voting
          message = await self.Tvoting.fetch_message(message.id); message: Message # update message
          reacts = message.reactions; reacts: List[Reaction]
          print(),print(),print(),print()
          print(reacts)
          prompts = [keywords[reactions[react.emoji]] for react in sorted(reacts, key= lambda react: react.count, reverse=True)[:4]]
          print("Voted for:")
          print(prompts)
          print("Stopgap means:")
          prompts += sample([kw for kw in keywords if kw not in prompts], 4-len(prompts))
          print(prompts)
          print(),print(),print(),print()
          thanks = await self.Tvoting.send("Thank you for voting")
          await message.delete(delay=2)
          await ping.delete()
          await thanks.delete()
      # Round cleanup
      for player in players:
        await player.remove_roles(self.Rcanvote)
        await player.remove_roles(self.Rspeaking)
      await self.goto_lobby(ctx)
      await self.say(ctx, msg="./audio/pre/the-round-has-concluded.wav")
    # Game wrapup
    await self.say(ctx, msg="./audio/pre/i-hope-you-enjoyed.wav")
    c = Path(f"./audio/rec/c{ulid.generate()}.txt")
    with open(c, "w+") as w:
      w.write("\n".join([f"file './{str(audio_file)}'" for audio_file in audio_files]))
      w.write("\n")
    ul = ulid.generate()
    o = Path(f"./audio/rec/o{ul}.wav")
    u = Path(f"./audio/rec/session-{datetime.now():%Y-%m-%d-%H-%M-%S}.webm")
    run(["ffmpeg", "-f", "concat", "-i", c, "-c", "copy", str(o)])
    run(["ffmpeg", "-i", str(o), "-c:a", "libopus", "-b:a", "128k", str(u)])
    print(),print(),print(),print()
    print("Done! Session recording at", str(u))
    print(),print(),print(),print()
    await self.say(ctx, msg="./audio/pre/thank-you-for-playing.wav")
    await self.Tlobby.send("Thank you for playing Tell Me, attached is the session recording", file=discord.File(str(u)))
    # Game cleanup
    for player in players:
        await player.remove_roles(self.Rcanvote, self.Rspeaking)
    await ctx.voice_client.disconnect()

  async def goto_lobby(self, ctx: Context):
    await ctx.voice_client.move_to(self.Vlobby)
    
  async def goto_talking(self, ctx: Context):
    await ctx.voice_client.move_to(self.Vtalking)

  async def bring_to_me(self, ctx: Context, user: discord.Member):
    "Bring a user to the bot's current location"
    print(ctx.voice_client.channel)
    await user.move_to(ctx.voice_client.channel)
  
  async def move_back(self, ctx: Context, user: discord.Member):
    "Move a user back to the lobby"
    await user.move_to(self.Vlobby)
  
  @bgm.before_invoke
  @play.before_invoke
  async def ensure_voice(self, ctx: Context):
    if ctx.voice_client is None:
      if ctx.author.voice:
        await ctx.author.voice.channel.connect()
      else:
        await ctx.send("I do not know which voice channel to join.")
        raise commands.CommandError("Unspecified voice channel.")
    elif ctx.voice_client.is_playing():
      ctx.voice_client.stop()

intent = discord.Intents.default()
# intent: discord.Intents
intent.members=True
intent.voice_states=True
intent.reactions=True
seed(time())
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), description="TellMe.py Bot for the TellMe System", intents=intent, chunk_guilds_at_startup=True)

@bot.event
async def on_ready():
  print(f"Logged in as {bot.user} ({bot.user.id})")
  print("------")

bot.add_cog(TellMe(bot))
bot.owner_id = 234272777446621185

@commands.is_owner()
@bot.command()
async def logout(ctx):
  if ctx.voice_client != None:
    await ctx.voice_client.disconnect()
  await ctx.bot.logout()

with open("../tellme-token.txt","r") as o: TOKEN=o.read().strip()
bot.run(TOKEN)
