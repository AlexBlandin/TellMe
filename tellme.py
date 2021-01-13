#!/usr/bin/env python3
import logging
import importlib
from random import sample
from pathlib import Path
from datetime import datetime
from math import isfinite

import asyncio
import discord
import pyttsx3
import youtube_dl
from ulid import ULID
from discord.ext import commands, tasks
from discord.ext.commands import Context
from parse import parse

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

tts = pyttsx3.init()
tts.setProperty("rate", 125)

extractor = Extractor()

ulid = ULID()
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
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
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track))
    ctx.voice_client.play(source, after=lambda e: print(f"Player error: {e}") if e else None)

  @commands.command()
  async def bgm(self, ctx: Context, *, query):
    """Plays from a local file or url (almost anything youtube_dl supports)"""
    if query in BGM or query.strip()=="":
      track = Path(f"./audio/bgm/{query if query in BGM else sample(BGM,1)[0]}")
      source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track))
      ctx.voice_client.play(source, after=lambda e: print(f"Player error: {e}") if e else None)
      await ctx.send(f"Now playing: {query}")
    else:
      async with ctx.typing():
        player = await YTDLSource.from_url(query, loop=self.bot.loop)
        ctx.voice_client.play(player, after=lambda e: print(f"Player error: {e}") if e else None)

      await ctx.send(f"Now playing: {player.title}")

  async def record(self, ctx: Context, *, time):
    time = min(10,float(time))
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()
    vc = ctx.voice_client
    recording = recording_folder / f"r{ulid.generate()}.wav"
    recording.touch(exist_ok=True)
    print(f"Recording {time}s in {str(recording)}")
    # vc.listen(discord.UserFilter(discord.WaveSink(str(audio)), ctx.author)) # whoever's turn it is
    vc.listen(discord.WaveSink(str(recording)))
    await asyncio.sleep(time-10)
    await self.alert(ctx) # Alert works, but audio was a little garbled immediately after, should be fine
    await asyncio.sleep(10)
    await asyncio.sleep(20) # latency adjustment (~10-15s, so cutting noise before would be nice)
    vc.stop_listening()
    print(f"Recording complete {str(recording)}")
    return recording

  @commands.command()
  async def say(self, ctx: Context, *, msg: str):
    f = Path(f"./audio/rec/r{ulid.generate()}.wav")
    f.touch(exist_ok=True)
    
    # TTS section
    importlib.reload(pyttsx3) # bc. pyttsx3 deadlocks on the second runAndWait
    tts = pyttsx3.init()
    tts.setProperty("rate", 125) # espeak is low quality
    tts.setProperty("voice", tts.getProperty("voices")[2].id)
    tts.save_to_file(msg, filename=str(f)) # but if we can save out then +1
    tts.runAndWait() # this blocks, we would like something fast
    tts.stop()
    
    # await ctx.send(msg) # Text option
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(f))
    ctx.voice_client.play(source, after=lambda e: print(f"Player error: {e}") if e else None)
    
    return f
    
    

  @commands.command()
  async def play(self, ctx: Context, *, query):
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
    self.join(ctx, channel=None)
    vc = ctx.voice_client
    players = self.Vlobby.members
    players = sample(players, len(players)) # shuffle
    for player in players:
      # player.add_roles()
      player.remove_roles(self.Rcanvote,self.Rspeaking)
    await self.say(ctx, msg=f"The turn order is: {' then '.join([player.display_name for player in players])}")
    await self.say(ctx, msg="I hope you enjoy playing TellMe!")
    await self.goto_talking(ctx)
    
    genre, location, item = "Horror", "Swiss Mountains", "Goat"
    prompts, last = [], ""
    
    # Gameloop
    for r in range(min(1,self.rounds)):
      print(f"Round {r}")
      # Roundloop
      for i, player in enumerate(players):
        player: discord.Member
        await self.bring_to_me(ctx, player)
        await player.add_roles(self.Rspeaking)
        if i == 0:
          await self.say(ctx, msg=f"Tell me a {genre} story set in {location} with {'' if item[-1]=='s' else 'an' if item[0] in 'aeiouh' else 'a'} {item}")
        else:
          await self.say(ctx, msg=f"The last sentence was: {last}")
          await self.say(ctx, msg=f"Your prompt words are: {' '.join(prompts)}")
        await self.say(ctx, msg=f"You will have {self.T} seconds to tell me a story. When there are ten seconds remaining, an alert will play. Your {self.T} seconds starts, now.")
        
        # recording = await self.record(ctx, time=90)
        time = min(15,float(self.T))
        vc = ctx.voice_client
        recording = recording_folder / f"r{ulid.generate()}.wav"
        recording.touch(exist_ok=True)
        print(f"Recording {time}s in {str(recording)}")
        vc.listen(discord.WaveSink(str(recording)))
        await asyncio.sleep(time-10)
        await self.alert(ctx)
        await asyncio.sleep(10)
        # "Done" but not really, latency compensation so don't close yet
        await self.say(ctx, msg="Your time is up.")
        
        await asyncio.sleep(20) # latency adjustment (~10-15s, so cutting noise before would be nice)
        vc.stop_listening()
        print(f"Recording complete {str(recording)}")
        
        
        
        
        await player.remove_roles(self.Rspeaking)
        await player.add_roles(self.Rcanvote)
        await self.move_back(ctx, player)
      # Round cleanup
      for player in players:
        player.remove_roles(self.Rcanvote)
    ...
    ...
    ...
    
    # message = await bot.send_message(channel, " ".join([f"{i}. {p}" for i, p in enumerate(prompts,start=1)])
    # reacts = [await bot.add_reaction(message, e) for e in ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "keycap_ten"]]
    await ctx.voice_client.disconnect()

  async def goto_lobby(self, ctx: Context):
    await ctx.voice_client.move_to(self.Vlobby)
  
  async def goto_talking(self, ctx: Context):
    await ctx.voice_client.move_to(self.Vtalking)

  async def bring_to_me(self, ctx: Context, user: discord.Member):
    "Bring a user to the bot's current location"
    await user.move_to(ctx.voice_client.channel)
  
  async def move_back(self, ctx: Context, user: discord.Member):
    "Move a user back to the lobby"
    await user.move_to(self.Vlobby)

  @play.before_invoke
  async def ensure_roles(self, ctx: Context):
    dget, server = discord.utils.get, ctx.guild
    vchannels, tchannels, roles = server.voice_channels, server.text_channels, server.roles
    self.Vlobby, self.Vtalking = dget(vchannels, name="Waiting Rooms"), dget(vchannels, name="Talking")
    self.Tlobby, self.Tvoting = ctx.channel, dget(tchannels, name="voting")
    self.Rcanvote, self.Rspeaking = dget(roles, name="TellMe-Voting"), dget(roles, name="TellMe-Speaking")
  
  @say.before_invoke
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

bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), description="TellMe.py Bot for the TellMe System")

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
