#!/usr/bin/python3
"""twitter

For harvesting tweets using the Twitter Search API.
"""

import sys
import time
import math
import json
import yaml
import argparse

import tweepy
import geocoder

import core
from comms.couchdb import CouchDBComms as db
from nlp.sentiment_analysis import SentimentAnalyser


class TweetHarvester():

    def __init__(self):
        """"""

        args = core.config('twitter', 'OAuth')
        # Initialise Twitter communication
        auth = tweepy.OAuthHandler(
            args['consumer_key'],
            args['consumer_secret']
        )
        auth.set_access_token(
            args['access_token'],
            args['access_token_secret']
        )
        try:
            self.api = tweepy.API(
                auth,
                wait_on_rate_limit=True,
                wait_on_rate_limit_notify=True
            )
            # tweepy.API constructor does not seem to throw an exception for
            # OAuth failure. Use API.verify_credentials() to validate OAuth
            # instead
            cred = self.api.verify_credentials()
            print (
                "OAuth connection with Twitter established through user @"
                + cred.screen_name
                + "\n"
            )
        except tweepy.TweepError as oauth_error:
            print ("OAuth connection with Twitter could not be established")
            raise oauth_error
        except:
            raise

        self.db_tweets = db('tweets')
        self.db_tweets_urls = db('tweets_urls')
        self.db_tweets_archive = db('tweets_archive')
        self.db_outlets = db('outlets')
        self.db_articles = db('articles')
        self.senti = SentimentAnalyser()

        self.id_to_outlet = self.db_outlets.get_users()
        self._update_since_ids()
        self.source_ext = {'api': [], 'wa': {}}

    def _update_since_ids(self):
        self.since_ids = self.db_tweets.get_since_ids()

    def _get_since_id(self, user_id):
        """Given a Twitter id, returns a since_id.

        Args:
            user_id (str/int):

        Returns:
            str:
            None:
        """
        try:
            since_id = self.since_ids[str(user_id)]
            return since_id
        except KeyError:
            return None
        except Exception as e:
            print(
                "Warning: An unexpected Exception was raised during "
                + "call to _get_since_id(): "
                + str(e)
            )
            return None

    def get_geocode(self, coordinates):
        """
        """
        try:
            g = geocoder.google(coordinates, method='reverse')
        except:
            raise
        geocode = {'geojson': g.geojson}
        return geocode

    def store_tweet(self, tweet_status, source=None):
        """Analyses and stores a tweet in the database.

        This method conducts sentiment analysis and geocoding on the
        tweet before attempting to store it in the database.

        Args:
            tweet_status (tweepy.Status):
            source (dict): Provenance data to store in the tweet.
        """
        # Convert the tweepy Status object into a dict
        tweet_str = json.dumps(tweet_status._json)
        tweet = json.loads(tweet_str)
        print("Processing tweet: " + tweet['id_str'])
        # Add source to tweet
        if source is None:
            source = {'api': [], 'wa': {}}
        tweet.update(source.copy())
        # If this tweet is from one of our outlets, store the outlet
        try:
            if tweet['user']['id_str'] in self.id_to_outlet:
                tweet['wa']['outlet'] = self.id_to_outlet[tweet['user']['id_str']]
        except Exception as e:
            print(
                "Warning: An unexpected Exception was raised in "
                + "checking for and assigning id_to_outlet."
            )
            pass
        # If this tweet is replying to one of our outlets, store the outlet
        try:
            if tweet['in_reply_to_user_id_str'] in self.id_to_outlet:
                tweet['wa']['reply_to'] = self.id_to_outlet[tweet['in_reply_to_user_id_str']]
        except KeyError:
            pass
        except Exception as e:
            print(
                "Warning: An unexpected Exception was raised in "
                + "checking for and assigning id_to_outlet."
            )
            pass
        # If this tweet mentions one of our outlets, store the outlet(s)
        try:
            if tweet['entities']['user_mentions']:
                for u in tweet['entities']['user_mentions']:
                    if u['id_str'] in self.id_to_outlet and u['id_str'] is not None:
                        if 'mentions' not in tweet['wa']:
                            tweet['wa']['mentions'] = []
                        tweet['wa']['mentions'].append(self.id_to_outlet[u['id_str']])
        except:
            pass
        # Convert the creation time to a UNIX timestamp
        try:
            tweet['wa']['time'] = core.get_time(tweet['created_at'])
        except Exception as e:
            print(
                "Warning: An unexpected Exception was raised in "
                + "converting created_at to a UNIX timestamp."
            )
            print(str(e))
            pass
        # Sentiment analysis
        sentiment = self.senti.analyse(tweet['text'])
        tweet.update(sentiment)
        # Geocoding
        if tweet['coordinates'] is not None:
            try:
                geocode = self.get_geocode(tweet['geo']['coordinates'])
                tweet.update(geocode)
            except:
                print(
                    "Warning: geocode() failed for tweet "
                    + tweet['id_str']
                )
                pass
        # If related to an article, store a duplicate of the tweet in
        # the URLs database
        if 'url' in tweet['wa']:
            response = self.db_tweets_urls.store_tweet(tweet)
            if response is not None:
                print("Stored tweet: " + tweet['id_str'] + " in URLs database.")
        # If the tweet is older than 28 days, store in the archive
        oldest_time = int(time.time() - 60*60*24*core.config('twitter', 'days'))
        if (int(tweet['wa']['time']) < oldest_time):
            response = self.db_tweets_archive.store_tweet(tweet)
            if response is not None:
                print("Stored tweet " + tweet['id_str'] + " in archive database.")
        else:
            response = self.db_tweets.store_tweet(tweet)
            if response is not None:
                print("Stored tweet " + tweet['id_str'] + " in database.")
        return response

    def iterate_timeline(self, user_id):
        """
        """
        # Download the timeline of the user
        try:
            since_id = self._get_since_id(user_id)
            for tweet in tweepy.Cursor(
                self.api.user_timeline,
                id=user_id,
                since_id=since_id
            ).items():
                try:
                    source = {'api': self.source_ext['api'][:],
                              'wa': self.source_ext['wa'].copy()}
                    source['api'].insert(0, {
                        'method': 'GET statuses/user_timeline',
                        'params': {
                            'user_id': str(user_id),
                            'since_id': since_id
                        }
                    })
                    self.store_tweet(tweet, source)
                except:
                    pass
        # Don't need to handle for RateLimitError, Cursor will wait
        except tweepy.TweepError as e:
            print(str(e))
            pass
        except Exception as e:
            print("Warning: Unexpected exception: " + str(e))
            pass

    def iterate_timelines(self):
        # Download list of users from the tweets database
        try:
            users_dict = self.db_outlets.get_users()
            users = list(users_dict)
        except:
            raise
        queue_len = len(users)

        node = core.config('node')
        processes = core.config('processes')

        if node is not None and processes is not None:
            chunk = int(math.floor(len(users) / int(processes)))
            start = int(node) * chunk
            end = start + chunk
        else:
            start = 0
            end = len(users)

        for num in range(start, end):
            self.iterate_timeline(users[num])

    def iterate_followers(self):
        # Download list of users from the tweets database
        try:
            users_dict = self.db_outlets.get_users()
            users = list(users_dict)
        except:
            raise
        queue_len = len(users)

        node = core.config('node')
        processes = core.config('processes')

        if node is not None and processes is not None:
            chunk = int(math.floor(len(users) / int(processes)))
            start = int(node) * chunk
            end = start + chunk
        else:
            start = 0
            end = len(users)

        for num in range(start, end):
            self.iterate_follower_timelines(users[num])

    def iterate_follower_timelines(self, user_id):
        # Download the tweets of the followers
        try:
            for follower in tweepy.Cursor(
                self.api.followers_ids,
                id=user_id
            ).items():
                self.source_ext['api'].insert(0, {
                    'method': 'GET followers/list',
                    'params': {
                        'user_id': str(user_id)
                    }
                })
                try:
                    if str(user_id) in self.id_to_outlet:
                        self.source_ext['wa']['follows'] = self.id_to_outlet[str(user_id)]
                except KeyError:
                    print(
                        "Warning: An unexpected KeyError exception was raised "
                        + "in checking for and assigning id_to_outlet."
                    )
                    pass
                # Download the timeline of the follower
                self.iterate_timeline(follower)
                self.source_ext['api'].pop(0)
                self.source_ext['wa'].pop('follows', None)
        # Don't need to handle for RateLimitError, Cursor will wait
        except tweepy.TweepError:
            pass
        except Exception as e:
            print("Warning: Unexpected exception: " + str(e))
            pass

    def iterate_retweets(self):
        """"""
        try:
            retweets = self.db_tweets.get_retweets()
            for r in retweets:
                try:
                    tweets = self.api.retweets(id=r)
                    for tweet in tweets:
                        source = {'api': self.source_ext['api'][:],
                                  'wa': self.source_ext['wa'].copy()}
                        source['wa']['retweet_of'] = r
                        source['wa']['retweet_of_outlet'] = retweets[r]
                        source['api'].insert(0, {
                            'method': 'GET statuses/retweets/:id',
                            'params': {
                                'id': r
                            }
                        })
                        self.store_tweet(tweet, source)
                except:
                    pass
        except:
            pass

    def iterate_articles(self, timerange='0'):
        """"""
        try:
            articles = self.db_articles.get_articles_list(timerange)
            for a in articles:
                url = list(a)[0]
                outlet = a[url]['outlet']
                try:
                    tweets = self.api.search(q=url)
                    for tweet in tweets:
                        source = {'api': self.source_ext['api'][:],
                                  'wa': self.source_ext['wa'].copy()}
                        source['wa']['url'] = url
                        source['wa']['url_outlet'] = outlet
                        source['api'].insert(0, {
                            'method': 'GET search/tweets',
                            'params': {
                                'q': url
                            }
                        })
                        self.store_tweet(tweet, source)
                except Exception as e:
                    print(str(e))
                    pass
        except Exception as e:
            print(str(e))
            pass

    def iterate_replies(self):
        """This method downloads tweets that tweets in our database
        have replied to.
        """
        try:
            replies = self.db_tweets.get_replies_full()
            for r in replies:
                try:
                    tweet = self.api.get_status(r)
                    reply = replies[r]['reply']
                    reply_user = replies[r]['reply_user']

                    source = {'api': self.source_ext['api'][:],
                              'wa': self.source_ext['wa'].copy()}
                    source['reply_status_id'] = int(reply)
                    source['reply_status_id_str'] = reply
                    source['reply_user_id'] = int(reply_user)
                    source['reply_user_id_str'] = reply_user
                    if reply_user in self.id_to_outlet:
                        soure['wa']['reply_outlet'] = self.id_to_outlet[reply_user]
                    source['api'].insert(0, {
                        'method': 'GET statuses/show/:id',
                        'params': {
                            'id': r
                        }
                    })
                    self.store_tweet(tweet, source)
                except:
                    pass
        except:
            pass


    class TweetStreamListener(tweepy.StreamListener):

        def on_status(self, status):
            print(status.text)

    def stream_tweets(self):
        tweetStreamListener = self.TweetStreamListener()
        melbourneStream = tweepy.Stream(auth = self.api.auth, listener=tweetStreamListener)
        melbourneStream.filter(locations=[144.4441,-38.5030,145.8176,-37.4018], async=True)

th = TweetHarvester()
while False:
    th.iterate_timelines()
    oldest_time = str(int(time.time() - 60*60*24*core.config('twitter', 'days')))
    th.iterate_articles(oldest_time)
while False:
    th.iterate_replies()
while False:
    th.iterate_retweets()
while False:
    th.iterate_articles()

#tweets = th.db_tweets.get_topic_tweets('rugby')
