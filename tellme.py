import discord
import logging
from discord.ext import commands
from parse import parse
# discord.AudioSource
# permissions 53540928: send messages ... attach files, add reactions, connect, speak, move members, use voice activity

# last sentence before prompt words, then "Your [T] seconds starts now"

with open("../tellme-token.txt","r") as o: TOKEN=o.read().strip()
bot = commands.Bot(">")
bot.owner_id = 234272777446621185

@commands.is_owner()
@bot.command()
async def tell(ctx):
  await ctx.send("TELL ME WHY AIN'T NOTHING BUT A HEART ACHE TELL ME WHY AIN'T NOTHING BUT A MISTAKE")

@commands.is_owner()
@bot.command()
async def logout(ctx):
  await ctx.bot.logout()

bot.run(TOKEN)
