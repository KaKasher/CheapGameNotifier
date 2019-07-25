import discord
import os
from discord.ext import commands, tasks
import logging

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get('DISCORD_TOKEN')
bot = commands.Bot(command_prefix='.', case_insensitive=True, help_command=None)

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

hunter = bot.get_cog('Hunter')


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game('.help to start'))
    refresh_games_notify_users.start()
    print('Bot is online.')

# For loading cogs
@bot.command()
async def load(ctx, extension):
    bot.load_extension(f'cogs.{extension}')

# For unloading cogs
@bot.command()
async def unload(ctx, extension):
    bot.unload_extension(f'cogs.{extension}')

# All of the help commands
@bot.command(aliases=['h'])
async def help(ctx, command=None):

    if command is not None:
        command = command.lower().strip()

    if command is None:
        help_embed = discord.Embed(description="To get more info about given command type: **.help** ***<command name>***\n\n",
                                   color=0xffff00)
        help_embed.set_author(name='Game Hunter Help')
        help_embed.add_field(name='Hunter help',
        value="**.wish** ***<your wished price> <allkeyshop url or game title>*** : adds the game to your wishlist\n"
              "**.wishlist** : displays your wishlist\n"
              "**.wishtable** : displays your wishlist in a table format\n"
              "**.wishdelete** ***<title>*** : removes a game from your wishlist\n"
              "**.wishupdate** ***<your wished price> <title>*** : updates your wished price in your wishlist\n\n"
              "Aliases: .h .w .wl .wd .wu")
        await ctx.send(embed=help_embed)

    elif command in ('wish', 'w', '.wish', '.w'):
        wish_help = discord.Embed(color=0xffff00)
        wish_help.add_field(name='Wish command',
        value="**.wish** ***<your wished price in €> <allkeyshop url or game title>*** : adds the game to your wishlist. "
              "You can use a title of a game instead of the url, if the game is in our database, it will be added. "
              "If the game isn't on allkeyshop.com you can provide a steam url\n\n"
              "Alias: .w\n\n"
              "Examples:\n"
              "`.w 12.5 Battlefield 5`\n"
              "`.wish 13.5 https://www.allkeyshop.com/blog/buy-battlefield-5-cd-key-compare-prices/`")
        await ctx.send(embed=wish_help)

    elif command in ('wishlist', 'wl', '.wishlist', '.wl'):
        wishlist_help = discord.Embed(color=0xffff00)
        wishlist_help.add_field(name='Wishlist command',
        value="**.wishlist** ***optional:<@user>*** : displays your wishlist.\n"
              "You can use @user as an optional argument to see that user's list\n\n"
              "Alias: .wl\n\n"
              "Example: `.wl @Bob#1337`")
        await ctx.send(embed=wishlist_help)

    elif command in ('wishtable', 'wt', '.wishtable', '.wt'):
        wishtable_help = discord.Embed(color=0xffff00)
        wishtable_help.add_field(name='Wishtable command',
        value="**.wishtable** ***optional:<@user>*** : displays your wishlist in a table format.\n"
              "You can use @user as an optional argument to see that user's list\n\n"
              "Alias: .wt\n\n"
              "Example: `.wt @Bob#1337`")
        await ctx.send(embed=wishtable_help)

    elif command in ('wishdelete', 'wd', '.wishdelete', '.wd'):
        wishdelete_help = discord.Embed(color=0xffff00)
        wishdelete_help.add_field(name='Wishdelete command',
        value="**.wishdelete** ***<title>*** : deletes a given title from your wishlist\n\n"
              "Alias: .wd\n\n"
              "Example: `.wd Minecraft`")
        await ctx.send(embed=wishdelete_help)

    elif command in ('wishupdate', 'wu', '.wishupdate', '.wu'):
        wishupdate_help = discord.Embed(color=0xffff00)
        wishupdate_help.add_field(name='Wishupdate command',
        value="**.wishupdate** ***<your wished price> <title>*** : Updates a given title in your wishlist.\n\n"
              "Alias: .wu\n\n"
              "Example: `.wu 5.21 Minecraft`")
        await ctx.send(embed=wishupdate_help)


@tasks.loop(hours=1)
async def refresh_games_notify_users():
    game_url_list = hunter.db_get_all_game_urls()
    hunter.db_update_all_games(game_url_list)
    user_id_list = hunter.db_get_all_user_id()

    for user_id in user_id_list:
        wish_list = hunter.db_get_user_wish_list(user_id)
        for wish in wish_list:
            _, wished_price, url, was_notified = wish
            game_record = hunter.db_get_game_record(url)
            title = game_record['title']
            merchant = game_record['merchant']
            actual_price = game_record['price']

            if actual_price <= wished_price and was_notified == 0:
                embed = discord.Embed(title=title, url=url, description="Price of the game has dropped!")
                embed.set_author(name="Your wish came true!")
                embed.add_field(name=merchant, value=actual_price, inline=True)

                user = await bot.fetch_user(user_id)
                await user.send(embed=embed)

                was_notified = 1
                hunter.db_set_notified(user_id, url, was_notified)

bot.run(TOKEN)
