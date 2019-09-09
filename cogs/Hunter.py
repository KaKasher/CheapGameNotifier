import requests
import asyncio
import sqlite3
import discord
from discord.ext import tasks, commands
from bs4 import BeautifulSoup
from prettytable import from_db_cursor
from os import system

ALLKEYSHOPURL = 'allkeyshop.com/blog/'
STEAMURL = 'store.steampowered.com/app/'

conn = sqlite3.connect('gamehunter.db')
c = conn.cursor()


class Hunter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Scrapes from the provided url, return's None if the url isn't allkeyshop or steam.
    def get_game_record(self, url):
        if ALLKEYSHOPURL.lower() in url.lower():
            r = requests.get(url)
            soup = BeautifulSoup(r.content, 'lxml')
            title = soup.find('span', {'itemprop': 'name'}).text.strip()
            cheapest_row = soup.find('div', {'class': 'offers-table-row'})
            merchant = cheapest_row.find('span', {'class': 'offers-merchant-name'}).text
            price = cheapest_row.find('span', {'itemprop': 'price'})['content']
            return {'title': title, 'merchant': merchant, 'price': price, 'url': url}
        elif STEAMURL.lower() in url.lower():
            currency_payload = {'cc': 'de'}
            r = requests.get(url, params=currency_payload)
            soup = BeautifulSoup(r.content, 'lxml')
            title = soup.find('span', {'itemprop': 'name'}).text.strip()
            price = soup.find('div', {'data-price-final': True})['data-price-final']
            price = price[:-2] + '.' + price[-2:]
            return {'title': title, 'merchant': 'steam', 'price': price, 'url': url}

        return None

    # Database manipulation functions

    # Adds a user record to users table
    def db_add_user(self, user_id, username):
        try:
            with conn:
                c.execute("INSERT INTO users VALUES (:user_id, :username)", {'user_id': user_id, 'username': username})
        except sqlite3.IntegrityError:
            pass

    # Adds a game record to games table
    def db_add_game(self, game_record):
        try:
            with conn:
                c.execute("INSERT INTO games VALUES (:title, :merchant, :price, :url)", game_record)
        except sqlite3.IntegrityError:
            pass
        except ValueError:
            pass

    # Adds a wish to wishlist table
    def db_add_wish(self, user_id, wished_price, url):
        try:
            with conn:
                c.execute("INSERT INTO wishlist VALUES (:user_id, :wished_price, :url, 0)",
                          {'user_id': user_id, 'wished_price': wished_price, 'url': url})
        except sqlite3.IntegrityError:
            return False

    # Returns a db_cursor for prettytable to print out using from_db_cursor()
    def db_get_user_wish_comm(self, user_id, table=False):
        with conn:
            wish = c.execute("""SELECT title, wished_price, price, merchant
            FROM wishlist, games
            WHERE user_id = :user_id AND wishlist.url = games.url""",
                             {'user_id': user_id})

        if table is True:
            return wish
        else:
            wish = c.fetchall()
            return wish

    # Returns all wishes for a given user from wishlist table
    def db_get_user_wish_list(self, user_id):
        with conn:
            c.execute("""SELECT * FROM wishlist WHERE user_id = :user_id""",
                             {'user_id': user_id})

            return c.fetchall()

    # Updates a game record in games table
    def db_update_game(self, game_record):
        with conn:
            c.execute("""UPDATE games 
            SET title = :title, price = :price, merchant = :merchant 
            WHERE url = :url""", game_record)

    # Returns a game record from games table, based on title or url
    def db_get_game_record(self, url=None, title=None):
        with conn:
            if url is not None:
                c.execute("""SELECT * FROM games WHERE url = :url""", {'url': url})
                record = c.fetchone()
            elif title is not None:
                c.execute("""SELECT * FROM games WHERE LOWER(title) = LOWER(:title) ORDER BY url DESC""",
                          {'title': title})
                record = c.fetchone()
            else:
                record = None

            if record is None:
                return None

            game_record = dict(zip(('title', 'merchant', 'price', 'url'), record))
            return game_record

    # Returns all urls from games table
    def db_get_all_game_urls(self):
        with conn:
            c.execute("""SELECT url FROM games""")
            urls = c.fetchall()
            gameUrlList = []
            for url in urls:
                gameUrlList.append(url[0])

            return gameUrlList

    # Updates all the game records in games table
    async def db_update_all_games(self, gameUrlList):
        for url in gameUrlList:
            game_record = self.get_game_record(url)
            self.db_update_game(game_record)
            print('Game updated:', game_record)
            await asyncio.sleep(1)

    # Returns all of the user id's from the users table
    def db_get_all_user_id(self):
        with conn:
            c.execute("""SELECT user_id FROM users""")
            users = c.fetchall()
            user_id_list = []
            for user in users:
                user_id_list.append(user[0])

            return user_id_list

    # Sets user's wish as notified in wishlist table
    def db_set_notified(self, user_id, url, notified=False):
        with conn:
            c.execute("""UPDATE wishlist 
            SET notified = :notified 
            WHERE user_id = :user_id AND url = :url""",
                      {'notified': notified, 'user_id': user_id, 'url': url})

    # Removes the wish from wishlist table for a given user provided a title
    def db_del_wish_command(self, user_id, title):
        with conn:
            c.execute("""DELETE FROM wishlist
            WHERE wishlist.url IN (SELECT games.url FROM games WHERE LOWER(games.title) = LOWER(:title)) 
            AND user_id = :user_id""",
                      {'title': title, 'user_id': user_id})

    # Updates user's wished price for a given title in wishlist table
    def db_update_wish_command(self, user_id, wished_price, title):
        with conn:
            c.execute("""UPDATE wishlist 
            SET wished_price = :wished_price 
            WHERE user_id = :user_id 
            AND wishlist.url IN (SELECT games.url FROM games WHERE LOWER(games.title) = LOWER(:title))""",
                      {'user_id': user_id, 'wished_price': wished_price, 'title': title})

    # Bot commands

    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f'Pong! {round(self.bot.latency * 1000)}ms')

    # Adds a wish
    @commands.command(aliases=['w'])
    async def wish(self, ctx, wished_price: float, *, url_or_title):
        # When the input is not an url, search database for a given title
        if url_or_title.lower().startswith('http') is False:
            record = self.db_get_game_record(title=url_or_title.strip())

            # If the game is not in the database, tell that to the user and quit
            if record is None:
                await ctx.send(':x: Game not found')
                return
            url_or_title = record['url']

        # If the game is not in the database games table, add it
        if self.db_get_game_record(url_or_title) is None:
            game_record = self.get_game_record(url_or_title)

            if game_record is None:
                await ctx.send('Invalid URL.')
                return

            self.db_add_game(game_record)

        username = f'{ctx.author.name}#{ctx.author.discriminator}'
        self.db_add_user(ctx.author.id, username)
        if self.db_add_wish(ctx.author.id, wished_price, url_or_title) is False:
            await ctx.send(':x: Game is already on your wishlist')
        else:
            await ctx.send(':white_check_mark: Game added to your wishlist!')

    @commands.command(aliases=['wt'])
    async def wishtable(self, ctx, member: discord.Member = None):
        if member is None:
            wishtable = self.db_get_user_wish_comm(ctx.author.id, True)
        else:
            wishtable = self.db_get_user_wish_comm(member.id, True)
        data = from_db_cursor(wishtable)

        await ctx.send(f"```{data}```")

    @commands.command(aliases=['wl'])
    async def wishlist(self, ctx, member: discord.Member = None):
        wishlist_embed = discord.Embed(color=0x00ff00)
        if member is None:
            wishlist = self.db_get_user_wish_comm(ctx.author.id)
            wishlist_embed.set_author(name=f"{ctx.author.name}'s wishlist")
        else:
            wishlist = self.db_get_user_wish_comm(member.id)
            wishlist_embed.set_author(name=f"{member.display_name}'s wishlist")

        for wish in wishlist:
            title, wished_price, actual_price, merchant = wish
            wishlist_embed.add_field(name=title, value=f'Wished price: {wished_price}€ | '
                                                       f'Actual price: {actual_price}€ | '
                                                       f'Merchant: {merchant}')

        await ctx.send(embed=wishlist_embed)



    @commands.command(aliases=['wd'])
    async def wishdelete(self, ctx, *, title):
        self.db_del_wish_command(ctx.author.id, title)
        await ctx.send('Wish deleted!')

    @commands.command()
    async def prank(self, ctx, member: discord.Member):
        if member.id == 304658956750422019:
            await ctx.send('A bana chcesz?')
            await ctx.author.move_to(None)
            return
        await member.move_to(None)

    @commands.command(aliases=['wu'])
    async def wishupdate(self, ctx, wished_price: float, *, title):
        self.db_update_wish_command(ctx.author.id, wished_price, title)
        await ctx.send('Wish updated!')

    # Error handling

    # @commands.Cog.listener()
    # async def on_command_error(self, ctx, error):
    #     if isinstance(error, commands.CommandNotFound):
    #         pass
    #     else:
    #         raise error

    @wish.error
    async def wish_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(':x: Missing Argument\n'
                           '\t\t**.wish** ***<your wished price in €> <allkeyshop url or game title>***')
        elif isinstance(error, commands.BadArgument):
            await ctx.send(':x: One of the arguments is invalid\n'
                           '\t\t**.wish** ***<your wished price in €> <allkeyshop url or game title>***')
        else:
            await ctx.send(':x: Invalid syntax\n'
                           '\t\ttype **.help wish** for help')
            raise error


    @wishlist.error
    async def wishlist_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(":x: One of the arguments is invalid\n"
                           "\t\t**.wishlist** ***<@Name>*** to see someone's wishlist")
        else:
            await ctx.send(':x: Invalid syntax\n'
                           '\t\ttype **.help wishlist** for help')
            raise error

    @wishtable.error
    async def wishtable_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(":x: One of the arguments is invalid\n"
                           "\t\t**.wishtable** ***<@Name>*** to see someone's wishlist")
        else:
            await ctx.send(':x: Invalid syntax\n'
                           '\t\ttype **.help wishlist** for help')
            raise error

    @wishdelete.error
    async def wishdelete_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(':x: Missing Argument\n'
                           '\t\t**.wishdelete** ***<title>***')
        else:
            await ctx.send(':x: Invalid syntax\n'
                           '\t\ttype **.help wishdelete** for help')
            raise error

    @wishupdate.error
    async def wishupdate_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(':x: Missing Argument\n'
                           '\t\t**.wishupdate** ***<your wished price> <title>***')
        elif isinstance(error, commands.BadArgument):
            await ctx.send(':x: One of the arguments is invalid\n'
                           '\t\t**.wishupdate** ***<your wished price> <title>***')
        else:
            await ctx.send(':x: Invalid syntax\n'
                           '\t\ttype **.help wishupdate** for help')
            raise error

def setup(bot):
    bot.add_cog(Hunter(bot))

