#!/usr/bin/python3
"""comms.couchdb

Classes inherited from DatabaseComms encapsulate database
communications. This is designed so that the database software can be
changed seamlessly without having to modify the rest of the codebase.
"""

import sys
import os
import json
import yaml

import couchdb

import core


class DatabaseComms:

    def __init__(self, db_str):
        """"""
        self.db_str = db_str
        self.connect()

    def connect(self):
        """"""


class CouchDBComms(DatabaseComms):
    """"""

    def connect(self):
        """"""
        args = core.config('couchdb')
        # Construct a URL from the arguments
        protocol = 'http'
        if 'https' in args:
            if args['https'] is True:
                protocol = 'https'
        # Create a safe URL that we can print (omits login/password)
        url = url_safe = '{protocol}://{ip}:{port}/'.format(
            protocol = protocol,
            ip = args['ip_address'],
            port = str(args['port'])
        )
        # Construct an updated URL if a login and password is supplied
        if ('login' in args) and ('password' in args):
            url = '{protocol}://{login}:{password}@{ip}:{port}/'.format(
                protocol = protocol,
                login = args['login'],
                password = args['password'],
                ip = args['ip_address'],
                port = str(args['port'])
            )
        # Attempt to connect to CouchDB server
        try:
            # Calling couchdb.Server will not throw an exception
            couch = couchdb.Server(url)
            # Attempt to GET from the CouchDB server to test connection
            couch.version()
            print("Connected to CouchDB server at " + url_safe)
        except ConnectionRefusedError:
            print("No CouchDB server at " + url_safe)
            raise
        except couchdb.http.Unauthorized as e:
            print("Connection to CouchDB server refused: " + str(e))
            raise
        except Exception as e:
            print(
                "Failed to connect to CouchDB server at "
                + url_safe
                + ". An unexpected exception was raised: "
                + str(e)
            )
            raise
        # Attempt to connect to CouchDB database
        try:
            self._db = couch[self.db_str]
            print ("Connected to database: " + self.db_str)
        # The python-couchdb docs says that a PreconditionFailed
        # exception is raised when a DB isn't found. But in practice it
        # throws a ResourceNotFound exception (CouchDB == 1.0.1)
        except couchdb.http.ResourceNotFound:
            try:
                self._db = couch.create(self.db_str)
                print ("Creating new database: " + self.db_str)
            except couchdb.http.Unauthorized:
                raise
            except Exception as e:
                raise
        except couchdb.http.Unauthorized:
            raise
        except Exception as e:
            raise
        # Update the design document
        self.update_views()

    def create_design_doc(self):
        """Returns a design document. Generates the MapReduce views
        from JavaScript files stored in the project.

        Returns:
            dict:
        """

        view_cat = self.db_str.split('_')[0]
        _id = '_design/' + view_cat

        # Create a blank new CouchDB design document
        design_doc = {'_id': _id,
                      'language': 'javascript',
                      'views': {}}
        # Save current working directory
        cwd = os.getcwd()
        # Change dir to where the MapReduce .js files are stored
        dir_path = os.path.dirname(os.path.realpath(__file__))
        os.chdir(dir_path + '/mapreduce')
        # Parse the MapReduce .js files
        for file in os.listdir():
            if file.endswith('.js'):
                if (file.split('_', 1)[0] == view_cat):
                    filename = file.split('_', 1)[1]
                    filename = os.path.splitext(filename)[0]
                    view = os.path.splitext(filename)
                    if design_doc['views'].get(view[0]) is None:
                        design_doc['views'][view[0]] = {}
                    if view[1] == '.map':
                        with open(file) as f:
                            map = f.read()
                        design_doc['views'][view[0]]['map'] = map
                    if view[1] == '.reduce':
                        with open(file) as f:
                            reduce = f.read()
                        design_doc['views'][view[0]]['reduce'] = reduce
        # Switch back to original current working directory
        os.chdir(cwd)
        # Return the design document
        return design_doc

    def update_views(self):
        """"""
        # Create a new design document
        design_doc = self.create_design_doc()
        # Retrieve the current design document
        current_doc = self._db.get(design_doc['_id'])
        # Test to see if the design document has changed
        if current_doc is not None:
            current_doc = dict(current_doc)
            test_doc = current_doc.copy()
            test_doc.pop('_rev', None)
            if (design_doc == test_doc):
                return
            design_doc.update({'_rev': current_doc['_rev']})
        # Save the design document to CouchDB
        self.store_dict(design_doc)

    def store_dict(self, doc, overwrite=False):
        """Stores a dict as a JSON document in CouchDB.

        Note: This method does not throw exceptions, it only prints
            warnings. This is because the application is intended for
            brute force data harvesting.

        Args:
            doc (dict): The dict that is to be stored in CouchDB.
            overwrite (bool): True to delete current doc in CouchDB
                and store the new one. Prevents revisioning.

        Returns:
            dict: If the save is successful this method will return a
                dict with doc._id (key) and doc._rev (value).

        Todo:
            * Need to handle CouchDB connection failure properly. Only
                provides a warning at the moment.
            * There is currently a critical error where overwriting a
                document fails. This occurs when the same document has
                performed an overwrite store in another database in the
                same CouchDB instance. A ResourceConflict Exception is
                raised when we try to store the new document (HTTP 409)
                despite the document being purged from the database.
        """
        if not isinstance(doc, dict):
            print(
                "Warning: store_dict() called, but doc input parameter"
                + " is not a dict."
            )
            return None
        # Attempt to save document to CouchDB
        try:
            response = self._db.save(doc)
            return response
        # If the _id already exists
        except couchdb.http.ResourceConflict as e:
            print(
                "Warning: The doc (_id: "
                + doc['_id']
                + ") is already in "
                + self.db_str
            )
            if overwrite is True:
                print(
                    "Overwriting doc (_id: "
                    + doc['_id']
                    + ") in "
                    + self.db_str
                )
                # Delete the document from the database
                for r in self._db.revisions(doc['_id']):
                    self._db.purge([{'_id': doc['_id'], '_rev': r.rev}])
                response = self.store_dict(doc, overwrite=False)
                return response
            pass
        # If the PUT request returns HTTP 404
        except couchdb.http.ResourceNotFound:
            print(
                "Warning: Attempted to save doc to database, but the "
                + "PUT request returned HTTP 404."
            )
            pass
        # If the CouchDB connection is underprivileged
        except couchdb.http.Unauthorized:
            print(
                "Warning: Attempted to save doc to database, but we "
                + "do not have permission."
            )
            pass
        # If it's an unknown error, continue for now, but warn the user
        except Exception as e:
            print(
                "Warning: Attempted to save doc to database, but we "
                + "encountered an unexpected Exception: "
                + str(e)
            )
            pass
        # Return None if we encountered an Exception
        return None

    def store_tweet(self, tweet, overwrite=False):
        """This method takes a tweet as an input and stores it in the
        database.

        This method encapsulates CouchDB specific operations
        (assigning an _id). If the tweet already exists in the database
        this method will do nothing.

        Args:
            tweet (dict): The tweet that is to be stored in the
                database. The dict should contain an id_str.

        Returns:
            dict: If the save is successful this method will return a
                dict with the doc._id (key) and doc._rev (value).
            None: If the save is unsuccessful.

        Todo:
            * This method could take multiple tweets as inputs and
                perform a CouchDB bulk insert.
            * This method could take an optional 'force' parameter to
                flag a revision update.
        """
        # Store the unique tweet ID as the document _id for CouchDB
        try:
            tweet.update({'_id': tweet['id_str']})
        except KeyError:
            print(
                "Warning: store_tweet() called, but tweet input "
                + "parameter does not contain an id_str."
            )
            return None
        except AttributeError:
            print(
                "Warning: store_tweet() called, but tweet input "
                + "parameter is not a dict."
            )
            return None
        # Attempt to store the dict in CouchDB
        response = self.store_dict(tweet, overwrite)
        return response

    def store_article(self, article):
        """This method takes an article as an input and stores it in
        the database.

        This method encapsulates CouchDB specific operations
        (assigning an _id). If the article already exists in the
        database this method will do nothing.

        Args:
            article (dict): The article that is to be stored in the
                database. The dict should contain a url.

        Returns:
            dict: If the save is successful this method will return a
                dict with the doc._id (key) and doc._rev (value).
            None: If the save is unsuccessful.

        Todo:
            * This method could take multiple articles as inputs and
                perform a CouchDB bulk insert.
            * This method could take an optional 'force' parameter to
                flag a revision update.
        """
        # Store the URL as the document _id for CouchDB
        try:
            article.update({'_id': article['url']})
        except KeyError:
            print(
                "Warning: store_article() called, but article input "
                + "parameter does not contain a url."
            )
            return None
        except AttributeError:
            print(
                "Warning: store_article() called, but article input "
                + "parameter is not a dict."
            )
            return None
        # Attempt to store the dict in CouchDB
        response = self.store_dict(article)
        return response

    def get_users(self):
        """Returns a dict of Twitter IDs and their corresponding
        outlets from the outlets database.
        """
        queue = {}
        try:
            for row in self._db.view('outlets/users', wrapper=None):
                if row.key is not None:
                    queue.update({row.key: row.value})
        except Exception as e:
            print ("Failed to retrieve view: "
                   + self._db.name
                   + "/outlets/_view/users")
            raise
        return queue

    def get_since_ids(self):
        """Returns a dict of Twitter user IDs as keys and the most
        recent tweet from that ID in the database as the values.
        """
        queue = {}
        try:
            for row in self._db.view('tweets/users_since_id',
                                     wrapper=None,
                                     group='true'):
                queue.update({row.key: row.value})
        except:
            raise Exception("Failed to retrieve view: "
                   + self._db.name
                   + "/tweets/_view/users_since_id?group=true")
        return queue

    def get_replies_full(self):
        """Retrieves a list of reply-to's that need to be
        downloaded.
        """
        queue = {}
        try:
            for row in self._db.view('tweets/replies_full',
                                     wrapper=None,
                                     group_level=1):
                if (row.value == 1):
                    queue.update({row.key[0]: {}})
            for row in self._db.view('tweets/replies_full',
                                     wrapper=None,
                                     group='true'):
                if row.key[0] in queue:
                    queue[row.key[0]]['reply'] = row.key[1]
                    queue[row.key[0]]['reply_user'] = row.key[2]
        except:
            raise Exception("Failed to retrieve view: "
                + self._db.name
                + "/tweets/_view/replies_full\n\n")
        return queue

    def get_crawler(self):
        """Returns XML sitemaps and RSS feeds to be crawled."""
        crawler = {}
        try:
            for row in self._db.view('outlets/crawler',
                                     wrapper=None):
                crawler.update({row.key: row.value})
        except:
            raise Exception("Failed to retrieve view: "
                + self._db.name
                + "/outlets/_view/crawler\n\n")
        return crawler

    def get_retweets(self):
        retweets = {}
        try:
            for row in self._db.iterview(
                'tweets/outlet_retweets',
                batch=1000,
                wrapper=None
            ):
                retweets.update({row.key: row.value})
        except:
            raise Exception("Failed to retrieve view: "
                + self._db.name
                + "/tweets/_view/outlet_retweets\n\n")
        return retweets

    def get_articles_list(self, timerange='0'):
        """Returns a dict of article URLs currently in the database and
        the revision numbers.
        """
        articles = []
        try:
            for row in self._db.iterview(
                'articles/opengraph',
                batch=1000,
                wrapper=None,
                descending='true',
                endkey=timerange
            ):
                try:
                    articles.append({
                        row.value['og']['url']: {
                            'outlet': row.value['wa']['outlet']
                        }
                    })
                except KeyError:
                    print(
                        "Warning: An unexpected exception was raised."
                    )
                    pass
                except AttributeError:
                    print(
                        "Warning: An unexpected exception was raised."
                    )
                    pass
        except:
            raise Exception("Failed to retrieve view: "
                + self._db.name
                + "/articles/_view/opengraph\n\n")
        return articles

    def get_opengraph(self, timerange='0'):
        articles = []
        try:
            for row in self._db.view('articles/opengraph',
                                     wrapper=None,
                                     descending='true',
                                     endkey=timerange
                                     ):
                articles.append(row.value)
        except:
            raise Exception("Failed to retrieve view: "
                + self._db.name
                + "/articles/_view/opengraph\n\n")
        return articles

    def get_topics(self, minimum=100):
        topics = {}
        try:
            for row in self._db.view(
                'tweets/topics',
                wrapper=None,
                group=True
            ):
                topics.update({row.key: row.value})
        except:
            raise
        sorted_topics = []
        for t in sorted(topics, key=topics.get, reverse=True):
            if (int(topics[t]) >= minimum):
                sorted_topics.append({t: topics[t]})
        return sorted_topics

    def get_topic_tweets(self, topic):
        map_fun = '''function(doc) {
          for (var i = 0; i < doc.features.length; i++) {
            if (doc.features[i] == "''' + topic + '''") {
              emit(doc.features[i], doc);
            }
          }
        }'''
        tweets = []
        for row in self._db.query(map_fun, reduce_fun=None,
            language='javascript', wrapper=None):
            tweets.append(row.value)
        sorted_tweets = sorted(tweets, key=lambda k: k['wa']['time'], reverse=True)
        return sorted_tweets

    def shard_tweets(self, timerange='0'):
        """This should basically work like this:
        IF tweet.wa.time IS LESS THAN input time
        DELETE FROM MAIN DB
        STORE IN NEW DB
        """
        return None
        print('retrieving view')
        count = 0
        try:
            for row in db_tweets._db.iterview(
                '_all_docs',
                batch=1000,
                wrapper=None
            ):
                count += 1
                tweet = dict(db_tweets._db.get(row.key))
                try:
                    print('Transferring tweet: ' + str(row.key) + '. wa.follows: ' + tweet['wa']['follows'] + '. No: ' + str(count))
                    db_tweets_test._db.save(tweet)
                    db_tweets._db.delete({'_id': row.key, '_rev': row.value['rev']})
                except KeyError:
                    print('Passing tweet.')
                    pass
                except couchdb.http.ResourceConflict:
                    db_tweets._db.delete({'_id': row.key, '_rev': row.value['rev']})
                except Exception as e:
                    print('process wrong')
                    print(str(e))
                    pass
        except Exception as e:
            print(str(e))
