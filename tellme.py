#!/usr/bin/env python3

#
# ████████╗███████╗██╗     ██╗     ███╗   ███╗███████╗   ██████╗ ██╗   ██╗
# ╚══██╔══╝██╔════╝██║     ██║     ████╗ ████║██╔════╝   ██╔══██╗╚██╗ ██╔╝
#    ██║   █████╗  ██║     ██║     ██╔████╔██║█████╗     ██████╔╝ ╚████╔╝
#    ██║   ██╔══╝  ██║     ██║     ██║╚██╔╝██║██╔══╝     ██╔═══╝   ╚██╔╝
#    ██║   ███████╗███████╗███████╗██║ ╚═╝ ██║███████╗██╗██║        ██║
#    ╚═╝   ╚══════╝╚══════╝╚══════╝╚═╝     ╚═╝╚══════╝╚═╝╚═╝        ╚═╝
#
# A Discord Bot to run TellMe sessions

# standard modules
import os
import json
import logging
from time import time
from typing import List
from pathlib import Path, PurePosixPath
from datetime import datetime
from subprocess import run, PIPE
from random import sample, shuffle, seed

# Quieten Tensorflow
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# pip modules (handled by poetry)
import asyncio
import discord
import librosa
from gtts import gTTS
import soundfile as sf
# import speech_recognition as sr
from discord.ext import commands
from discord.ext.commands import Context
from discord import VoiceChannel, TextChannel, Role, Message, Reaction, Member, Guild

# Thanks to imayhaveborkedit's patches (semi-up to date by Gorialis) we have audio recording
# pip install -U "discord.py[voice] @ git+https://github.com/Gorialis/discord.py@voice-recv-mk3"

# local modules
from ytdl import YTDLSource
from extractor import Extractor

extractor = Extractor()

discord.opus.load_opus("opus")
if not discord.opus.is_loaded():
  raise ModuleNotFoundError(f"Tried to load opus but failed, so TellMe.py is unable to run", name = "opus")

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO) # logging.WARNING # logging.ERROR
handler = logging.FileHandler(filename = "discord.log", encoding = "utf-8", mode = "w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)

class TellMe(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    # TODO: Setup talking & voting as separate channels (can delete?)
    #       Lobbies are wherever they're called from
    # TODO: Setup roles
    # TODO: Get genre,location,item from files
    # TODO: Gamemodes & templates from files would be nice, but need to do something for that... dict we can pass to a `.setrules(template,**gm)`
    self.Vlobby, self.Vtalking = None, None # Voice Channels
    self.Tlobby, self.Tvoting = None, None # Text Channel
    self.Rcanvote, self.Rspeaking = None, None # Roles
    self.players = []
    self.rounds, self.T = 1, 90
    self.round, self.turn = 0, 0
    self.prompts, self.last = [], ""
    self.genre, self.location, self.item = "", "", ""
    self.keywords = []
    self.audio_files = []
    seed(time())
    
    self.SFX = [f.name for f in Path("./audio/sfx/").glob("*")] # Some nice SFX to use (for "login" etc only right now)
    """
    S: Up Chime 2 by FoolBoyMedia | License: Attribution
    S: Flourish Spacey 1 by GameAudio | License: Creative Commons 0
    S: gotItem.mp3 by Kastenfrosch | License: Creative Commons 0
    """
    
    self.BGM = [f.name for f in Path("./audio/bgm/").glob("*")] # Some nice BGM to use
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
    
    shuffle(self.SFX)
    shuffle(self.BGM)
  
  @commands.is_owner()
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
  async def setrounds(self, ctx: Context, *, n: int):
    self.rounds = max(1, int(n))
    await ctx.send(f"Now playing for {self.rounds} rounds")
  
  @commands.command()
  async def volume(self, ctx: Context, *, volume: float):
    """Changes the player's volume"""
    volume = float(volume)
    if int(volume) == 0: volume = int(volume * 100)
    else: volume = int(volume)
    
    if ctx.voice_client is None:
      return await ctx.send("Not connected to a voice channel.")
    ctx.voice_client.source.volume = int(volume / 100)
    await ctx.send(f"Changed volume to {int(volume)}%")
  
  @commands.command()
  async def stop(self, ctx: Context):
    if ctx.voice_client is not None and ctx.voice_client.is_playing():
      ctx.voice_client.stop()
  
  @commands.command()
  async def pause(self, ctx: Context):
    if ctx.voice_client is not None and ctx.voice_client.is_playing():
      ctx.voice_client.pause()
  
  @commands.command()
  async def resume(self, ctx: Context):
    if ctx.voice_client is not None and ctx.voice_client.is_paused():
      ctx.voice_client.resume()
  
  @commands.command()
  async def bgm(self, ctx: Context, *, query):
    """Plays from a local file or url (almost anything youtube_dl supports)"""
    if query in self.BGM or query.strip() == "any":
      track = Path(f"./audio/bgm/{query if query in self.BGM else sample(self.BGM,1)[0]}")
      source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track))
      ctx.voice_client.play(source, after = lambda e: print(f"Player error: {e}") if e else None)
      await ctx.send(f"Now playing: {query}")
    else:
      async with ctx.typing():
        player = await YTDLSource.from_url(query, loop = self.bot.loop)
        ctx.voice_client.play(player, after = lambda e: print(f"Player error: {e}") if e else None)
      
      await ctx.send(f"Now playing: {player.title}")
  
  @commands.command()
  async def play(self, ctx: Context):
    """Plays TellMe"""
    
    dget, server = discord.utils.get, ctx.guild
    server: Guild
    vchannels, tchannels, roles = server.voice_channels, server.text_channels, server.roles
    self.Vlobby, self.Vtalking = dget(vchannels, name = "Waiting Room"), dget(vchannels, name = "Talking")
    self.Tlobby, self.Tvoting = ctx.channel, dget(tchannels, name = "voting")
    self.Rcanvote, self.Rspeaking = dget(roles, name = "TellMe-Voting"), dget(roles, name = "TellMe-Speaking")
    self.Vlobby: VoiceChannel
    self.Vtalking: VoiceChannel
    self.Tlobby: TextChannel
    self.Tvoting: TextChannel
    self.Rcanvote: Role
    self.Rspeaking: Role
    
    await self.say(ctx, msg = "./audio/pre/welcome-to-tellme.wav")
    # await self.join(ctx, channel=None)
    vc = ctx.voice_client
    
    self.players = vc.channel.members
    self.players = [player for player in self.players if player.bot == False]
    shuffle(self.players)
    self.players: List[Member]
    for player in self.players:
      await player.remove_roles(self.Rspeaking, self.Rcanvote)
    print(), print(), print(), print()
    turn_order = f"The turn order is: {' then '.join([player.display_name for player in self.players])}"
    print(turn_order)
    print(), print(), print(), print()
    await ctx.send(turn_order)
    await self.say(ctx, msg = turn_order)
    await self.say(ctx, msg = "./audio/pre/i-shall-begin-shortly.wav")
    
    await asyncio.sleep(0.5)
    await self.goto_talking(ctx)
    await asyncio.sleep(5)
    
    self.genre = sample([
      "Action", "Animation", "Comedy", "Crime", "Experimental", "Fantasy", "Historical ", "Horror", "Romance", "Sci-fi",
      "Romance", "Thriller", "Western", "Psychological"
    ], 1)
    self.location = sample([
      "Farm", "Palace", "Kingdom", "Paris", "Jungle", "Desert ", "Field", "Town", "City", "London", "Italy", "Spain",
      "Germany", "Portugal", "Poland", "Dubai", "Las Vegas", "California ", "Cardiff"
    ], 1)
    self.item = sample([
      "cup", "phone", "microphone", "pen", "paper", "computer", "mantle", "guitar", "map", "pill", "sword", "gun",
      "knife", "nuts", "coal", "steel", "brick", "rope", "foil", "kettle", "headphones"
    ], 1)
    self.prompts, self.last = [], ""
    
    self.audio_files = [] # in order of occurence
    
    # Gameloop
    for _round in range(min(1, self.rounds)):
      self.round = _round
      print(f"Round {self.round}")
      # Roundloop
      for _turn, player in enumerate(self.players):
        self.turn = _turn
        await self.bring_to_me(ctx, player)
        await player.add_roles(self.Rspeaking)
        await asyncio.sleep(5) # wait to see if it moves
        
        print("Rundown")
        if self.turn == 0 and self.round == 0:
          s = await self.say(
            ctx,
            msg =
            f"Tell me a {self.genre} story set in {self.location} with {'' if self.item[-1]=='s' else 'an' if self.item[0] in 'aeiouh' else 'a'} {self.item}"
          )
          self.audio_files.append(s)
        else:
          s = await self.say(ctx, msg = f"The last sentence was. {self.last}.")
          self.audio_files.append(s)
          print("Prompts:")
          print(self.prompts)
          s = await self.say(ctx, msg = f"Your prompt words are. {', '.join(self.prompts)}.")
          self.audio_files.append(s)
        print("Get ready")
        
        time = max(15, int(self.T))
        s = await self.say(
          ctx,
          msg =
          f"You will have {time} seconds to tell me a story. You should hear an alert when there are ten seconds remaining. Your {time} seconds starts, now."
        )
        self.audio_files.append(s)
        
        recording = await self.record(ctx, resample = True)
        
        await player.add_roles(self.Rcanvote)
        await self.move_back(ctx, player)
        await player.remove_roles(self.Rspeaking)
        
        self.keywords, self.last = extractor.extract(str(recording))
        if self.turn != len(self.players) - 1:
          await self.vote(ctx, keywords = self.keywords)
      
      # Round cleanup
      for player in self.players:
        await player.remove_roles(self.Rcanvote)
        await player.remove_roles(self.Rspeaking)
      
      # await self.goto_lobby(ctx)
      # await self.say(ctx, msg="./audio/pre/the-round-has-concluded.wav")
    
    # Game wrapup
    await self.goto_lobby(ctx)
    await asyncio.sleep(3)
    await self.say(ctx, msg = "./audio/pre/i-hope-you-enjoyed.wav")
    
    # WARNING: Changed Path to PurePosixPath as otherwise was getting problems on my machine. Shouldn't affect your machine
    # Also added a extra str() for c as I think that was needed
    
    c = PurePosixPath(f"./audio/c{datetime.now():%Y-%m-%d-%H-%M-%S}.txt")
    with open(c, "w+") as w:
      w.write("\n".join([f"file '{str(audio_file.parent.name)}/{audio_file.name}'" for audio_file in self.audio_files]))
      w.write("\n")
    u = Path(f"./audio/session-{datetime.now():%Y-%m-%d-%H-%M-%S}.m4a")
    run(["ffmpeg", "-f", "concat", "-safe", "0", "-loglevel", "panic", "-i", c, u])
    
    await self.say(ctx, msg = "./audio/pre/thank-you-for-playing.wav")
    await self.Tlobby.send(
      "Thank you for playing Tell Me, attached is the session recording", file = discord.File(str(u))
    )
    
    # Game cleanup
    for player in self.players:
      await player.remove_roles(self.Rcanvote, self.Rspeaking)
    
    print("And we're done, disconnecting now")
    await ctx.voice_client.disconnect()
  
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
  
  async def say(self, ctx: Context, msg: str):
    if msg[:12] == "./audio/pre/":
      f = Path(msg) # pre-recorded
    else:
      ul = f"{datetime.now():%Y-%m-%d-%H-%M-%S}"
      f = Path(f"./audio/rec/r{ul}.wav")
      m = Path(f"./audio/rec/r{ul}.mp3")
      gTTS(msg).save(str(m))
      run(["ffmpeg", "-loglevel", "panic", "-i", m, f])
      # m.unlink()
    wait = float(
      json.loads(
        run(["ffprobe", "-i", f, "-loglevel", "quiet", "-print_format", "json", "-show_streams"],
            encoding = "utf-8",
            stdout = PIPE).stdout
      )["streams"][0]["duration"]
    ) + 0.5
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(f))
    ctx.voice_client.play(source, after = lambda e: print(f"Player error: {e}") if e else None)
    await asyncio.sleep(wait) # wait for speech to pass
    return f
  
  async def record(self, ctx: Context, resample = True):
    # Start recording
    print("Start")
    vc = ctx.voice_client
    recording_folder = Path("./audio/rec/")
    recording_folder.mkdir(parents = True, exist_ok = True)
    recording = recording_folder / f"r{datetime.now():%Y-%m-%d-%H-%M-%S}.wav"
    recording.touch(exist_ok = True)
    time = max(15, int(self.T))
    print(f"Recording {time}s in {str(recording)}")
    vc.listen(discord.WaveSink(str(recording)))
    await asyncio.sleep(time - 10)
    await self.alert(ctx)
    await asyncio.sleep(10)
    # Done, we can stop momentarily
    if ctx.voice_client.is_playing():
      ctx.voice_client.stop()
    s = await self.say(ctx, msg = "./audio/pre/your-time-is-up.wav")
    if self.turn != len(self.players) - 1:
      await self.say(ctx, msg = "./audio/pre/momentarily-you-will-be.wav")
    else:
      await self.say(ctx, msg = "./audio/pre/the-round-has-ended.wav")
    await asyncio.sleep(5)
    vc.stop_listening()
    if resample: # resample so that we can stitch with gTTS output, if that is not done, then can be avoided
      resampled, samplerate = librosa.load(str(recording), samplerate = 24000)
      sf.write(str(recording), resampled, samplerate, subtype = "PCM_16", endian = "LITTLE")
    self.audio_files.append(recording)
    self.audio_files.append(s)
    print(), print(), print(), print()
    print(f"Recording complete {str(recording)}")
    print(), print(), print(), print()
    return recording
  
  async def vote(self, ctx: Context, keywords = None):
    if keywords is not None and keywords is not [] and keywords != self.keywords:
      self.keywords = keywords
    ping = await self.Tvoting.send("Please vote on the following prompts by selecting the corresponding number:")
    message = await self.Tvoting.send(" ".join([f"{i}. {p} " for i, p in enumerate(self.keywords, start = 1)]))
    message: Message
    reactions = {}
    for k, (n,
            e) in zip(self.keywords, enumerate(["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"])):
      await message.add_reaction(e)
      await asyncio.sleep(0.5)
      reactions[e] = n
      print(k, end = " ")
    print()
    await asyncio.sleep(20) # 20s voting period for voting
    message = await self.Tvoting.fetch_message(message.id)
    message: Message # update message
    reacts = message.reactions
    reacts: List[Reaction]
    self.prompts = [
      self.keywords[reactions[react.emoji]]
      for react in sorted(reacts, key = lambda react: react.count, reverse = True)[:4]
    ]
    print("Voted for:")
    print(self.prompts)
    if len(self.prompts) < 4:
      print("Stopgap means:")
      self.prompts += sample([kw for kw in self.keywords if kw not in self.prompts], 4 - len(self.prompts))
      print(self.prompts)
    thanks = await self.Tvoting.send("Thank you for voting")
    await message.delete(delay = 2)
    await ping.delete(delay = 2)
    await thanks.delete(delay = 10)
  
  async def alert(self, ctx: Context):
    track = Path(f"./audio/sfx/{sample(self.SFX,1)[0]}")
    shuffle(self.SFX)
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track))
    ctx.voice_client.play(source, after = lambda e: print(f"Player error: {e}") if e else None)
  
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

# permissions 321976400: manage roles & channels, send messages ... attach files, add reactions, connect, speak, move members, use voice activity

# Intents necessary for TellMe.py at this moment
intent = discord.Intents.default()
intent: discord.Intents
intent.members = True
intent.voice_states = True
intent.reactions = True
seed(time())
bot = commands.Bot(
  command_prefix = commands.when_mentioned_or("!"),
  description = "TellMe.py Bot for the TellMe System",
  intents = intent,
  chunk_guilds_at_startup = True
)

@bot.event
async def on_ready():
  print(f"Logged in as {bot.user} ({bot.user.id})")
  print("------")

bot.add_cog(TellMe(bot))

@commands.is_owner()
@bot.command()
async def logout(ctx):
  if ctx.voice_client is not None:
    await ctx.voice_client.disconnect()
  await ctx.bot.logout()

with open("token.txt", "r") as o:
  TOKEN = o.read().strip()
with open("owner.txt", "r") as o:
  OWNER = {int(l.strip()) for l in o.readlines()} # 1 per line
bot.owner_ids = OWNER or {234272777446621185}
bot.run(TOKEN)
