import discord
import logging
from discord.ext import commands
# discord.AudioSource
# permissions 53540928: send messages ... attach files, add reactions, connect, speak, move members, use voice activity

with open("../tellme-token.txt","r") as o: TOKEN=o.read().strip()
bot = commands.Bot(">")
bot.owner_id = 234272777446621185

@commands.is_owner()
@bot.command()
async def ping(ctx):
  await ctx.send("Running")

@commands.is_owner()
@bot.command()
async def logout(ctx):
  await ctx.bot.logout()

bot.run(TOKEN)