import logging
from random import sample
from pathlib import Path

import asyncio
import discord
import youtube_dl
from discord.ext import commands
from parse import parse
# discord.AudioSource
# permissions 53540928: send messages ... attach files, add reactions, connect, speak, move members, use voice activity

# last sentence before prompt words, then "Your [T] seconds starts now"

SFX=[f.stem for f in Path("./audio/sfx/").glob("*")] # Some nice SFX to use (for "login" etc only right now)
"""
S: Up Chime 2 by FoolBoyMedia | License: Attribution
S: Flourish Spacey 1 by GameAudio | License: Creative Commons 0
S: gotItem.mp3 by Kastenfrosch | License: Creative Commons 0
"""

BGM=[f.stem for f in Path("./audio/bgm/").glob("*")] # Some nice BGM to use
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
  async def join(self, ctx, *, channel: discord.VoiceChannel):
    """Joins a voice channel"""
    if ctx.voice_client is not None:
      return await ctx.voice_client.move_to(channel)
    await channel.connect()

  @commands.command()
  async def record(self, ctx, *, time):

    await asyncio.sleep(time)

  @commands.command()
  async def setup(self, ctx, *, args):
    """Configure TellMe - either by voice or by the command"""

    await asyncio.sleep(5)

  @commands.command()
  async def play(self, ctx, *, query):
    """Plays the game"""
    await asyncio.sleep(5)

  @commands.command()
  async def bgm(self, ctx, *, query):
    """Plays from a local file or url (almost anything youtube_dl supports)"""
    if query in BGM or query.strip()=="":
      track = next(Path("./audio/bgm/").glob(f"{query if query in BGM else sample(BGM,1)}.*"))
      source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track))
      ctx.voice_client.play(source, after=lambda e: print(f"Player error: {e}") if e else None)
      await ctx.send(f"Now playing: {query}")
    else:
      async with ctx.typing():
        player = await YTDLSource.from_url(query, loop=self.bot.loop)
        ctx.voice_client.play(player, after=lambda e: print(f"Player error: {e}") if e else None)

      await ctx.send(f"Now playing: {player.title}")

  @commands.command()
  async def volume(self, ctx, volume: int):
    """Changes the player's volume"""

    if ctx.voice_client is None:
      return await ctx.send("Not connected to a voice channel.")

    ctx.voice_client.source.volume = volume / 100
    await ctx.send(f"Changed volume to {volume:.0%}")

  @commands.command()
  async def stop(self, ctx):
    """Stops and disconnects the bot from voice"""
    await ctx.voice_client.disconnect()

  @bgm.before_invoke
  @play.before_invoke
  @setup.before_invoke
  @record.before_invoke
  async def ensure_voice(self, ctx):
    if ctx.voice_client is None:
      if ctx.author.voice:
        await ctx.author.voice.channel.connect()
      else:
        await ctx.send("I am not connected to a voice channel.")
        raise commands.CommandError("Not connected to a voice channel.")
    elif ctx.voice_client.is_playing():
      ctx.voice_client.stop()
  
  @join.after_invoke
  async def alert(self, ctx):
    track = next(Path("./audio/sfx/").glob(f"{sample(SFX,1)}.*"))
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track))
    ctx.voice_client.play(source, after=lambda e: print(f"Player error: {e}") if e else None)
    print(f"Connected as {self.bot.user}")


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
  await ctx.bot.logout()

with open("../tellme-token.txt","r") as o: TOKEN=o.read().strip()
bot.run(TOKEN)
