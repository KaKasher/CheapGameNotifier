import requests
import sqlite3
from bs4 import BeautifulSoup

ALLKEYSHOPURL = 'allkeyshop.com/blog/'
STEAMURL = 'store.steampowered.com/app/'

conn = sqlite3.connect('cheapestgame.db')
c = conn.cursor()


def main():
    while True:
        username = input("input your username: ")
        add_user(username)

        # print('1. Add new game to watch list  ')
        # print('2. See your game list')
        # user_input = input('Make selection: ')
        # if user_input == '1':
        #     url = input('Paste in the url from allkeyshop/steam: ')
        #     #price_desired = input('Input a desired price in euro: ')
        #     if get_game_record(url) not in GAMELIST:
        #         GAMELIST.append(get_game_record(url))
        # if user_input == '2':
        #     for record in GAMELIST:
        #         for value in record.values():
        #             print(value, end=' ')
        #         print(end='\n')



#def update_price_desired(price_desired):

def get_game_record(url):
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

def add_user(username):
    with conn:
        c.execute("INSERT INTO users VALUES (NULL, :username)", {'username': username})

def add_game(game_record):
    with conn:
        c.execute("INSERT INTO games VALUES (:title, :merchant, :price, :url)", game_record)


if __name__ == '__main__':
    main()
    conn.close()
