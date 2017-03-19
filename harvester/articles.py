#!/usr/bin/python3
""""""

import time
import datetime

from comms.couchdb import CouchDBComms as db

db_articles = db('articles')

days = 3
current_time = time.time()
timestamp = current_time - (60*60*24*days)
timestamp = str(timestamp)

articles = db_articles.get_opengraph(timestamp)

print('\n\n##### ARTICLES IN THE PAST ' + str(days) + ' DAY(S) #####\n\n')

for a in articles:
    print('title:   ' + a['og']['title'])
    try:
        print(
            'date:    ' +
            datetime.datetime.fromtimestamp(
                int(a['wa']['publish_time'])
            ).strftime('%Y-%m-%d %H:%M:%S')
        )
    except:
        pass
    try:
        print('author:  ' + a['article']['author']['username'])
    except KeyError:
        pass
    try:
        print('website: ' + a['og']['site_name'])
    except KeyError:
        pass
    print('url:     ' + a['og']['url'])
    try:
        if isinstance(a['og']['image'], dict):
            print('image:   ' + a['og']['image']['content'])
        else:
            print('image:   ' + a['og']['image'])
    except:
        pass
    print('')

#print(articles)
