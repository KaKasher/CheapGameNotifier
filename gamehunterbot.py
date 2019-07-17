import discord
import os
from discord.ext import commands


TOKEN = 'NjAwOTU1NTkzMjM4MzgwNTcz.XS8VPg.p5dbtYDSu4YMSx-ocvumSPbfbdo'
bot = commands.Bot(command_prefix='.')


@bot.event
async def on_ready():
    print('Bot is online.')


@bot.command()
async def load(ctx, extension):
    bot.load_extension(f'cogs.{extension}')


@bot.command()
async def unload(ctx, extension):
    bot.unload_extension(f'cogs.{extension}')


for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')


bot.run(TOKEN)
