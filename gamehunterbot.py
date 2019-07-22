import discord
import os
from discord.ext import commands, tasks
import logging

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get('DISCORD_TOKEN')
bot = commands.Bot(command_prefix='.')


@bot.event
async def on_ready():
    refresh_games_notify_users.start()
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

hunter = bot.get_cog('Hunter')





@tasks.loop(minutes=10)
async def refresh_games_notify_users():
    print('loop started')
    # game_url_list = hunter.db_get_all_game_urls()
    # hunter.db_update_all_games(game_url_list)
    # print('Game list has been updated!')
    user_id_list = hunter.db_get_all_user_id()

    for user_id in user_id_list:
        wish_list = hunter.db_get_user_wish_list(user_id)
        for wish in wish_list:
            _, wished_price, url, was_notified = wish
            game_record = hunter.db_get_game_record(url)
            title = game_record['title']
            merchant = game_record['merchant']
            actual_price = game_record['price']

            print(wished_price, actual_price, was_notified, actual_price <= wished_price and was_notified is False)
            if actual_price <= wished_price and was_notified == 0:
                print('in if')
                embed = discord.Embed(title=title, url=url, description="Price of the game has dropped!")
                embed.set_author(name="Your wish came true!")
                embed.add_field(name=merchant, value=actual_price, inline=True)
                print('after embed')

                user = await bot.fetch_user(user_id)
                print('after fetch')
                await user.send(embed=embed)

                was_notified = 1
                hunter.db_set_notified(user_id, url, was_notified)

bot.run(TOKEN)
