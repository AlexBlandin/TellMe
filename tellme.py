import logging
from random import sample
from pathlib import Path
from datetime import datetime

import asyncio
import discord
import youtube_dl
from ulid import ULID
from discord.ext import commands, tasks
from discord.ext.commands import Context
from parse import parse

# Thanks to imayhaveborkedit's patches (semi-up to date by Gorialis) we have audio recording
# pip install -U "discord.py[voice] @ git+https://github.com/Gorialis/discord.py@voice-recv-mk3"

# permissions 53540928: send messages ... attach files, add reactions, connect, speak, move members, use voice activity

# last sentence before prompt words, then "Your [T] seconds starts now"

# lib = next(Path("/").rglob("libopus0.so"))
lib = Path("/usr/lib/x86_64-linux-gnu/libopus.so.0.7.0")
discord.opus.load_opus(lib)
print(f"Audio working" if discord.opus.is_loaded() else "Uh oh", str(lib))

ulid = ULID()
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)

waves_folder = Path("./audio/rec/")
waves_folder.mkdir(parents=True, exist_ok=True)

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

  @commands.command()
  async def join(self, ctx: Context, *, channel: discord.VoiceChannel):
    """Joins a voice channel"""
    # await ctx.author.voice.channel.connect()
    if ctx.voice_client is not None:
      return await ctx.voice_client.move_to(channel)
    await channel.connect()
    await self.alert(ctx)

  @commands.command()
  async def record(self, ctx: Context, *, time):
    time = float(time)
    time += ctx.voice_client.average_latency
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()
    vc = ctx.voice_client
    wave_file = waves_folder / f"r{ulid.generate()}.wav"
    wave_file.touch(exist_ok=True)
    print(f"Recording {str(wave_file)}")
    vc.listen(discord.WaveSink(str(wave_file)))
    await asyncio.sleep(time)
    vc.stop_listening()
    print(f"Recording complete {str(wave_file)}")
    await ctx.send("Recording complete.")


  @commands.command()
  async def setup(self, ctx: Context, *, args):
    """Configure TellMe - either by voice or by the command"""

    await asyncio.sleep(5)

  @commands.command()
  async def play(self, ctx: Context, *, query):
    """Plays the game"""
    await asyncio.sleep(5)

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

  @commands.command()
  async def volume(self, ctx: Context, volume: int):
    """Changes the player's volume"""

    if ctx.voice_client is None:
      return await ctx.send("Not connected to a voice channel.")

    ctx.voice_client.source.volume = volume / 100
    await ctx.send(f"Changed volume to {volume:.0%}")

  @commands.command()
  async def stop(self, ctx: Context):
    """Stops and disconnects the bot from voice"""
    await ctx.voice_client.disconnect()
  
  @commands.command()
  async def alert(self, ctx: Context):
    track = Path(f"./audio/sfx/{sample(SFX,1)[0]}")
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track))
    ctx.voice_client.play(source, after=lambda e: print(f"Player error: {e}") if e else None)
    await ctx.send(f"In {ctx.voice_client.channel}")

  @bgm.before_invoke
  @play.before_invoke
  @setup.before_invoke
  @record.before_invoke
  async def ensure_voice(self, ctx: Context):
    if ctx.voice_client is None:
      if ctx.author.voice:
        await ctx.author.voice.channel.connect()
      else:
        await ctx.send("I am not connected to a voice channel.")
        raise commands.CommandError("Not connected to a voice channel.")
    elif ctx.voice_client.is_playing():
      ctx.voice_client.stop()

bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), description="TellMe.py Bot for the TellMe System")

@bot.event
async def on_ready():
  print(f"Logged in as {bot.user} ({bot.user.id})")
  print("------")

bot.add_cog(TellMe(bot))
bot.owner_id = 234272777446621185
KDBot = 414925323197612032

@commands.is_owner()
@bot.command()
async def tell(ctx):
  await ctx.send("TELL ME WHY AIN'T NOTHING BUT A HEART ACHE TELL ME WHY AIN'T NOTHING BUT A MISTAKE")

@commands.is_owner()
@bot.command()
async def logout(ctx):
  if ctx.voice_client != None:
    await ctx.voice_client.disconnect()
  await ctx.bot.logout()

with open("../tellme-token.txt","r") as o: TOKEN=o.read().strip()
bot.run(TOKEN)
