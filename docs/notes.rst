Development notes
-----------------

Development notes: bugs/fixes and potential improvements.

comms
-----
* Need to decide whether or not the different databases should be declared
within the class, or whether each database is accessed through their own unique
instantiation of the class

comms.nectar
------------
* There is currently a bug in using the method
boto.s3.connection.S3Connection.get_bucket() with python3 (boto == 2.42.0). The
current fix is to pass validate=False to the method.

opengraph
---------
* parse_rss(): There is currently a bug in using bs4 (4.5.1) with lxml (3.3.3)
when parsing RSS .xml files. BeautifulSoup mungs the <link></link> tags and
turns them into a single <link/> tag. The current fix is to pass 'xml' to the
BeautifulSoup() constructor rather than 'lxml'.
http://stackoverflow.com/questions/13961831/why-is-beautifulsoup-unable-to-correctly-read-parse-this-rss-xml-document
