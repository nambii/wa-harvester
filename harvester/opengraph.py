#!/usr/bin/python3
"""opengraph

Harvests open graph data from XML sitemaps and RSS feeds.
"""

import re
import requests
import time
from urllib import robotparser
from urllib.parse import urlsplit

import facebook
import bs4
from bs4 import BeautifulSoup

#sys.path.append(os.path.abspath("/home/ubuntu/wa-twitter/harvester/"))

import core
from comms.couchdb import CouchDBComms as db
from comms.nectar import ObjectStore


class OGHarvester():
    """

    Todo:
        * Need a method that allows you reparse a URL, so it can be called
            from the CMS
    """

    def __init__(self):
        """"""
        # Connect to the outlets database
        self.db_outlets = db('outlets')
        # Connect to database to store articles
        self.db_articles = db('articles')
        # Connect to the Object Store to store media files
        self.obj = ObjectStore('wa-opengraph')

    def parse_url(self, url, force=False):
        """Attempt to GET a given URL.

        This method ensures that the exception handling is consistent
        across all methods which parse URLs.

        Args:
            url (str): The URL to be parsed.
            force (bool): Set to True to ignore robots.txt advice.
                False by default.

        Returns:
            requests.models.Response:

        Raises:
            ConnectionError:
        """
        if force is False:
            # Find base URL from URL
            base_url = '{0.scheme}://{0.netloc}/'.format(urlsplit(url))
            # Test if the robots.txt file allows search engine access
            rp = robotparser.RobotFileParser()
            rp.set_url(base_url + 'robots.txt')
            rp.read()
            # Raise an exception if we are not allowed access to URL
            if rp.can_fetch('*', url) is False:
                raise Exception(
                    base_url
                    + "robots.txt rejected crawler access to: "
                    + url
                )

        # Attempt to retrieve the URL
        try:
            response = requests.get(url)
        except ConnectionError as e:
            #print ("Invalid URL or network error.")
            raise
        except Exception as e:
            #print ("Could not retrieve URL: " + url)
            raise
        # Raise an exception if not a successful HTTP status code
        if response.status_code != 200:
            raise Exception(
                "Invalid response from the URL ("
                + url
                + ").\nHTTP status code: "
                + str(response.status_code)
                + "."
            )
        return response

    def parse_sitemap(self, url):
        """Returns a dict of URLs based on an XML sitemap

        Need to modify the method to be able to parse multiple:
        <image:image>
            <image:loc></image:loc>
            <image:caption></image:caption>
        </image:image>

        Args:
            url (str): The URL of the XML sitemap to be parsed.

        Returns:
            dict:

        Raises:
            Raises any exceptions caught from attemping to GET the
            URL, and raises an Exception if the response content does
            not contain a valid XML sitemap schema.
        """
        print(core.dt() + "Crawling sitemap at " + url + ". ", end="")
        # Create an empty dict for the articles
        articles = {}
        # Attempt to retrieve the URL
        try:
            response = self.parse_url(url)
        except Exception as e:
            print(str(e))
            return articles
            #raise
        # Record the parse time and remove decimal places
        parse_time = int(time.time())
        # Record crawl data
        crawl = {'time': str(parse_time), 'url': url}
        # Use BeautifulSoup to parse the web page
        soup = BeautifulSoup(response.content, "lxml")
        # Find all <url> tags in the web page
        urls = soup.findAll('url')
        # Raise an exception if there are no <url> tags in the web page
        if not urls:
            #raise Exception("The URL (" + url + ") contains no <url> tags.")
            return articles
        # Extract the data for each URL into a dict
        for u in urls:
            if u.find('loc') is not None:
                sitemap = self.parse_tag(u)
                if 'lastmod' in sitemap:
                    sitemap['lastmod_time'] = core.get_time(sitemap['lastmod'])
                sitemap['crawl'] = crawl
                articles[sitemap['loc']] = {'url': sitemap['loc'],
                    'sitemap': sitemap}
        # Return the dict
        return articles

    def parse_rss(self, url):
        """
        This method currently does not raise any exceptions. It returns
        an empty dict with a warning if the URL is invalid.

        Args;
            url (str): The URL of the RSS feed to be parsed.

        Returns:
            dict: Empty if invalid URL.
        """
        print(core.dt() + "Crawling RSS feed at " + url + ". ", end="")
        # Create an empty dict for the articles
        articles = {}
        # Attempt to retrieve the URL
        try:
            response = self.parse_url(url)
        except:
            print("! Warning: No response from URL " + url)
            return articles
            # raise
        # Record the parse time and remove decimal places
        parse_time = int(time.time())
        # Record crawl data
        crawl = {'time': str(parse_time), 'url': url}
        # Use BeautifulSoup to parse the web page
        soup = BeautifulSoup(response.content, 'xml')
        # Find all <item> tags in the web page
        items = soup.findAll('item')
        # Raise an exception if there are no <item> tags in the web page
        if not items:
            # raise Exception("The URL (" + url + ") contains no <item> tags.")
            print("! Warning: No <item> tags in URL " + url)
            return articles
        # Extract the RSS attributes
        rss_tag = soup.find('rss')
        if rss_tag is None:
            rss_tag = soup.find('rdf')
        if rss_tag is None:
            rss_tag = soup.find('RDF')
        rss_attrs = self.split_namespace(rss_tag.attrs)
        #print(rss_tag.attrs)
        # Extract the channel information
        channel = {}
        channel_soup = soup.find('channel')
        for e in channel_soup(['item']):
            e.extract()
        channel = self.parse_tag(channel_soup)
        # Extract the data for each URL into a dict
        for i in items:
            if i.find('link') is not None:
                item = self.parse_tag(i)
                if 'pubDate' in item:
                    item['pubDate_time'] = core.get_time(item['pubDate'])
                rss = rss_attrs
                rss['item'] = item
                rss['crawl'] = crawl
                articles[item['link']] = {'url': item['link'],
                    'rss': rss}
        # Return the dict
        return articles

    def parse_tag(self, tags):
        """This method takes a bs4.element.Tag as an input and returns
        a dict.

        Preserves duplicate tags by creating a list of dicts.
        Preserves namespaces
        Preserves attributes by creating dict (normally <key>value</key> to
        be compact, but <key subkey="subvalue">content="subvalue"</key> if
        needed)

        For simplicity in code, tags wtihout a namespace are assigned one.

        Mostly if/else because bs4 does not throw many exceptions
        """
        return_dict = {}
        for tag in tags:
            if type(tag) is bs4.element.Tag:
                tag_dict = {}
                # Assign a namespace for this tag
                if tag.prefix is not None:
                    namespace = tag.prefix
                else:
                    namespace = 'none'
                if namespace not in return_dict:
                    return_dict[namespace] = {}
                # If this tag has children tags
                if bool(tag.findChildren()) is True:
                    tag_dict = self.parse_tag(tag)
                    # Kill any namespaces from child tags, although
                    # they can be retained if needed (remove code)
                    if tag.prefix in tag_dict:
                        tag_dict = tag_dict[tag.prefix]
                # Store the tag contents
                else:
                    if bool(tag.attrs) is True:
                        tag_dict = tag.attrs
                        tag_dict['content'] = tag.string
                    else:
                        tag_dict = tag.string

                # If there is already a tag there with the same name, it needs to be a list
                if tag.name in return_dict[namespace]:
                    # Make it a list if not one already
                    if type(return_dict[namespace][tag.name]) is not list:
                        tmp_dict = return_dict[namespace][tag.name]
                        return_dict[namespace][tag.name] = [tmp_dict]
                    # Append new data
                    return_dict[namespace][tag.name].append(tag_dict)
                # Else save the new tag
                else:
                    return_dict[namespace][tag.name] = tag_dict

        # Move 'none' namespace dict into parent dict, if 'none' exists
        return_dict.update(return_dict.pop('none', {}))
        # Return the dict
        return return_dict

    def parse_article(self, url):
        """Returns metadata for a webpage.
        """

        print(core.dt() + "Parsing article: " + url)
        # If the URL is for media content, return an empty dict
        if url.endswith('.mp3') or url.endswith('.pdf'):
            return {}
        # Attempt to retrieve the URL
        try:
            response = self.parse_url(url)
        except:
            raise
        # Record the parse time and remove decimal places
        parse_time = int(time.time())
        # Use BeautifulSoup to parse the web page
        soup = BeautifulSoup(response.content, 'lxml')
        # Find all <meta> tags in the web page
        metatags = soup.findAll('meta')
        # Create an empty dict for the metadata
        meta = {}
        # Store Open Graph and Twitter metadata
        for m in metatags:
            for attr in ['property', 'name']:
                if m.has_attr(attr):
                    meta[m[attr]] = m['content']
                    # If the meta value is an image
                    for ext in ['.jpg', '.jpeg', '.gif', '.png',
                        '.bmp', '.tiff']:
                        if re.search(ext, m['content'].lower()) is not None:
                            # Try and store it in the Object Store, and
                            # replace the link with our own one
                            try:
                                meta[m[attr]] = self.obj.store(m['content'])
                            #!! Improve exception handling !!
                            except:
                                pass
        try:
            meta = self.split_namespace(meta)
        except Exception as e:
            print(str(e))
        # Store other metadata
        if soup.find('title') is not None:
            meta['title'] = soup.find('title').string
        # Create a new dict for the article
        article = {'meta': meta}
        # Store full HTML document
        html = response.content.decode(response.encoding)
        article['html'] = html
        ### Store article content
        # Try to narrow down the soup
        if soup.find('article') is not None:
            soup_small = soup.find('article')
        elif soup.find('body') is not None:
            soup_small = soup.find('body')
        else:
            soup_small = soup
        # Remove irrelevant elements
        for e in soup_small(['head', 'header', 'nav', 'aside', 'footer',
                             'script', 'noscript', 'style', 'meta', 'button',
                             'source', 'img', 'path', 'svg', 'form', 'embed',
                             'menu', 'iframe']):
            e.extract()
        # Get string
        text = soup_small.get_text()
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        article['text'] = text
        # Store the crawl time
        article['crawl'] = {'time': str(parse_time)}
        return article

    def intuit_og(self, article):
        """Construct an Open Graph object.

        Args:
            article (dict): Requires 'url' and 'outlet' as keys.

        Returns:
            dict:

        Todo:
            * If using an RSS description which contains HTML markup,
                we should process the content using BeautifulSoup to
                extract both text ('og:description') and an <img>
                ('og:image') if one exists.
            * Support the following properties:
                og:type, og:audio, og:video
            * Perhaps rename the method (infer, deduce, interpet)
        """

        def process(ogp, article, path, lists):
            """

            Todo:
                * This could become a more standard method in the
                    project because it allows us to create structured
                    data from semi-structured data.
            """
            if traverse(ogp, [path]) is None:
                value = traverse(article, lists)
                if value is not None:
                    for key in reversed(path):
                        value = {key: value}
                    ogp = self.merge(ogp, value)
            return ogp

        def traverse(article, lists):
            """

            Args:
                lists (list): This should be a list of lists.

            Returns:

            """
            for path in lists:
                tmp = article.copy()
                try:
                    for key in path:
                        tmp = tmp[key]
                    return tmp
                except KeyError:
                    pass
            return None

        ogp = {'wa': {'outlet': article['outlet']}}
        if 'meta' in article:
            for key in ['og', 'article', 'music', 'video', 'book', 'profile']:
                if key in article['meta']:
                    ogp[key] = article['meta'][key]

        if 'og' not in ogp:
            ogp['og'] = {}
        ogp['og']['url'] = article['url']
        ogp = process(ogp=ogp, article=article,
            path=['og', 'title'],
            lists=[
                ['meta', 'twitter', 'title'],
                ['rss', 'item', 'title'],
                ['meta', 'title']
            ])
        ogp = process(ogp=ogp, article=article,
            path=['og', 'image'],
            lists=[
                ['meta', 'twitter', 'image'],
                ['rss', 'channel', 'image']
            ])
        ogp = process(ogp=ogp, article=article,
            path=['og', 'description'],
            lists=[
                ['meta', 'twitter', 'description'],
                ['meta', 'description'],
                ['rss', 'item', 'description']
            ])
        if 'og' in ogp:
            if 'description' not in ogp['og']:
                try:
                    desc_soup = BeautifulSoup(
                        article['rss']['item']['description'],
                        'lxml'
                    )
                    #kill formatting
                except KeyError:
                    pass
        ogp = process(ogp=ogp, article=article,
            path=['og', 'site_name'],
            lists=[
                ['rss', 'channel', 'title']
            ])
        ogp = process(ogp=ogp, article=article,
            path=['article', 'published_time'],
            lists=[
                ['rss', 'item', 'pubDate'],
                ['rss', 'item', 'dc', 'date']
            ])
        ogp = process(ogp=ogp, article=article,
            path=['article', 'modified_time'],
            lists=[
                ['meta', 'og', 'updated_time'],
                ['sitemap', 'lastmod']
            ])
        # wa:publish_time
        if 'article' in ogp:
            if 'published_time' in ogp['article']:
                publish_time = core.get_time(ogp['article']['published_time'])
                ogp['wa']['publish_time'] = publish_time
            elif 'modified_time' in ogp['article']:
                publish_time = core.get_time(ogp['article']['modified_time'])
                ogp['wa']['publish_time'] = publish_time
        ogp = process(ogp=ogp, article=article,
            path=['article', 'author'],
            lists=[
                ['meta', 'article', 'author'],
                ['rss', 'item', 'dc', 'creator']
            ])
        try:
            author = ogp['article']['author']
            if isinstance(author, str):
                ogp['article']['author'] = {'username': author}
        except KeyError:
            pass
        # article:section - string - A high-level section name. E.g. Technology
        # article:tag - string array
        ogp = process(ogp=ogp, article=article,
            path=['article', 'tag'],
            lists=[
                ['rss', 'item', 'category'],
                ['meta', 'keywords']
            ])
        try:
            tag = ogp['article']['tag']
            if isinstance(tag, str):
                tag = tag.split(',')
                for i in range(0, len(tag)):
                    tag[i] = tag[i].strip()
                ogp['article']['tag'] = tag
            elif isinstance(tag, dict):
                if 'content' in tag:
                    ogp['article']['tag'] = [tag['content']]
                else:
                    ogp['article']['tag'] = list(tag)
            elif isinstance(tag, list):
                for i in range(0, len(tag)):
                    if isinstance(tag[i], dict):
                        if 'content' in tag[i]:
                            ogp['article']['tag'][i] = tag[i]['content']
        except KeyError:
            pass
        # Return the dict
        return ogp

    def reanalyse_article(self, url):
        """Future method. This method should take the HTML stored in
        the CouchDB document, reanalyse it and store it as a new
        revision. This method will be used to ensure database
        consistency when modifications are made to this classes source
        code.
        """
        try:
            article = self.db_articles._db.get(url)
            soup = BeautifulSoup(article['html'], 'lxml')
            #do stuff
            self.db_articles.store_article(article)
        except:
            pass
        return None

    def split_namespace(self, old_dict):
        """Takes a dict and if the key has a colon, then create a
        subdict.
        """
        new_dict = {}

        for key in old_dict:
            # Turn it into a nested dict
            tmp = old_dict[key]
            split_key = key.split(':')
            for s in reversed(split_key):
                tmp = {s: tmp}
            # Merge it into the main dict
            new_dict = self.merge(new_dict, tmp)

        return new_dict

    def merge(self, a, b, path=None):
        """merges dict b into a
        """
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self.merge(a[key], b[key], path + [str(key)])
                # If we are inserting a key/value into a key/dict
                elif isinstance(a[key], dict) and not isinstance(b[key], dict):
                    tmp = b[key]
                    b[key] = {'content': tmp}
                    self.merge(a[key], b[key], path + [str(key)])
                # If we are inserting a key/dict into a key/value
                elif not isinstance(a[key], dict) and isinstance(b[key], dict):
                    tmp = a[key]
                    a[key] = {'content': tmp}
                    self.merge(a[key], b[key], path + [str(key)])
                # Same leaf value
                elif a[key] == b[key]:
                    pass
                else:
                    #raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
                    pass
            else:
                a[key] = b[key]
        return a

    def iterate(self, outlet=None):
        """"""
        # Retrieve a dict of XML sitemaps and RSS feeds
        urls = self.db_outlets.get_crawler()
        # Create a list of articles that are currently stored in the db
        self.articles_list = {}
        articles = self.db_articles.get_articles_list()
        for a in articles:
            self.articles_list.update(a)

        # If an outlet is passed as an argument, then isolate the
        # relevant URLs
        if outlet is not None:
            for u in list(urls):
                if (urls[u] != outlet):
                    urls.pop(u, None)

        articles = {}
        # Discover new content from aggregators
        for u in urls:
            count = 0
            new_articles = {}
            new_articles = self.parse_aggregator(u)
            # Detect which articles we already have archived and
            # add the new ones to the master list
            for n in new_articles:
                new_articles[n]['outlet'] = urls[u]
                if n not in self.articles_list:
                    if n not in articles:
                        articles[n] = {}
                    articles[n].update(new_articles[n])
                    count += 1
            print(str(count) + " new articles found.")

        # Call list() to make a copy of articles.keys() since the dict
        # size will change during iteration
        count = 0
        for a in list(articles):
            try:
                # Parse the article
                articles[a].update(self.parse_article(a))
                # Intuit the open graph properties
                articles[a]['ogp'] = self.intuit_og(articles[a])
                # Attempt to store it in the database. Pop the article
                # from the dict to reduce memory usage.
                try:
                    self.db_articles.store_article(articles.pop(a))
                    count += 1
                except:
                    pass
            except Exception as e:
                print(core.dt() + "Failed to parse article: " + str(e))
                pass

        print(core.dt() + "Successfully archived " + str(count) + " new articles.\n")

    def parse_aggregator(self, url):
        articles = {}
        try:
            response = self.parse_url(url)
            soup = BeautifulSoup(response.content, 'xml')
            if soup.find('urlset') is not None:
                articles = self.parse_sitemap(url)
            elif soup.find('rss') is not None:
                articles = self.parse_rss(url)
            elif soup.find('rdf') is not None:
                articles = self.parse_rss(url)
            elif soup.find('RDF') is not None:
                articles = self.parse_rss(url)
            else:
                print(core.dt() + "No schema detected for: " + url)
        except Exception as e:
            print(str(e))
        return articles

    def parse_web_archive(self):
        urls = {}
        wbs = {
            'http://web.archive.org/web/*/https://www.buzzfeed.com/allanclarke.xml': 'allan_clarke'
        }

        for wb in wbs:
            response = requests.get(wb)
            soup = BeautifulSoup(response.content, 'lxml')
            links = soup.findAll('a')

            for l in links:
                if 'href' in l.attrs:
                    url = l.attrs['href']
                    if '.xml' in url or '/rss' in url or '/feed' in url:
                        if '*' not in url:
                            if '/web/' in url:
                                url = 'http://web.archive.org' + url
                                urls.update({url: wbs[wb]})
            time.sleep(2)
        return urls

    def reform_ogp(self, outlet=None):
        # Create a list of articles that are currently stored in the db
        self.articles_list = {}
        articles = self.db_articles.get_articles_list()
        for a in articles:
            for url in a:
                if outlet is not None:
                    if (a[url]['outlet'] == outlet):
                        self.articles_list.update(a)
                else:
                    self.articles_list.update(a)

        count = 0
        for url in self.articles_list:
            count += 1
            article = dict(self.db_articles._db.get(url))
            if 'manual' not in article['ogp']:
                print(str(count) + ": Parsing url: " + url)
                try:
                    ogp = self.intuit_og(article)
                    article['ogp'] = ogp
                    self.db_articles.store_article(article)
                except:
                    print('something fucked up')

##################
## Main Program ##
##################

og_harvester = OGHarvester()
while True:
    og_harvester.iterate()
    minutes = 5;
    print(core.dt() + "Sleeping for " + str(minutes) + " minutes.")
    time.sleep(minutes*60)

#og_harvester.reform_ogp()

#articles = og_harvester.parse_rss('https://www.buzzfeed.com/allanclarke.xml')
#print(articles)
