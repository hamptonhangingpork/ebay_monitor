import time, html, sys, requests, json, urllib3, urllib.parse, os, itertools
from bs4 import BeautifulSoup
from re import sub, search
from discord.ext import tasks
import discord
import dns
import asyncio
import lxml
#import ssl
from keep_alive import keep_alive
from discord_webhook import DiscordWebhook, DiscordEmbed
import warnings
import pymongo
warnings.filterwarnings("ignore")


keep_alive()

#insert discord webhook here
webhook_url = []

mongo_p = #insert mongo password here
mongo_u = #insert mongo username here
mongo_url = #insert mongo url here

while True:
	try:
		# open db and get keywords
		server_client = pymongo.MongoClient(f"mongodb+srv://{mongo_u}:{mongo_p}@{mongo_url}/")
		db = server_client["ebay_monitor"]
		collection = db['keywords']
		product_db = db['product_list']
        # search ebay for ea kw
		for kw in collection.find({}):
			keyword = kw['title'].replace(" ", "+")
			added_flag = kw['newly_added']
            # load last 2 pages
			for i in range(1,2):
				ebayUrl = f"https://www.ebay.com/sch/i.html?_from=R40&_nkw={keyword}&_sacat=176985&_sop=10&_pgn={str(i)}"
				print(f"[-] Querying [{ebayUrl}]")
				r= requests.get(ebayUrl)
				data=r.text
				soup=BeautifulSoup(data, 'lxml')
    
				product_list = []
    
				listings = soup.find_all('li', attrs={'class': 's-item'})
                
				for listing in listings:
					for url in listing.find_all('a', attrs={'class': 's-item__link'}):
						item_info = dict()
						prod_url = url.get('href')
						item_id = search(r"(\d+)\?", prod_url).group(1)
						if item_id != '123456':
							item_info[item_id] = dict()
							item_info[item_id]['prod_url'] = prod_url
							if prod_url:
								name = listing.find('h3', attrs={'class':"s-item__title"})
								prod_name = name.text if not name.text.startswith("New Listing") else name.text[11:]
								prod_name = prod_name.encode("ascii", "ignore")
								prod_name = prod_name.decode()
								item_info[item_id]['prod_name'] = prod_name
                                    
								price = listing.find('span', attrs={'class':"s-item__price"})
								prod_price = price.text
								item_info[item_id]['prod_price'] = prod_price
                                
								thumbnail = listing.find('img', attrs={'class':"s-item__image-img"}) 
								thumbnail_url = thumbnail.get('src')
								item_info[item_id]['thumbnail_url'] = thumbnail_url
								product_list.append(item_info)
				time.sleep(5)
            
			print("[-] Checking items")
            # for each item found in this request
			for item in product_list:
				for key in item:
					if not product_db.find_one({'item_id': key}):
						if not added_flag:
							embed = DiscordEmbed(title=item[key]['prod_name'], url=item[key]['prod_url'])
							embed.add_embed_field(name='eBay ID', value=key, inline=False)
							embed.add_embed_field(name='Price', value=item[key]['prod_price'], inline=False)
							embed.add_embed_field(name='Match Keyword', value=kw['title'], inline=False)
							embed.set_image(url=item[key]['thumbnail_url'])
                      
  						# attach the embed to the webhook request and go!
							for server_webhook in webhook_url:
								webhook = DiscordWebhook(url=server_webhook)
								webhook.add_embed(embed)
								webhook.execute()
								time.sleep(5) # to prevent Discord webhook rate limiting
                
                        # add post name to DB so we don't display it again
						product_db.insert_one({'item_id': key, 'prod_name': item[key]['prod_name'], 'prod_url': item[key]['prod_url'], 'prod_price': item[key]['prod_price'], 'thumbnail_url': item[key]['thumbnail_url']})
            

			collection.find_one_and_update({'title': kw['title']}, {'$set': {'newly_added': False}})
			time.sleep(5)
		time.sleep(300)
	except Exception as e:
		print(e)
		time.sleep(30)