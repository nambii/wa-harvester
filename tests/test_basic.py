#!/usr/bin/python3
""""""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(sys.path[0]), 'harvester'))

import core
from comms.couchdb import CouchDBComms
from comms.nectar import ObjectStore

# Check that the config file is complete
args = core.config()
# couchdb
# Required args: ip_address, port
# Optional args: https, login, password


obj_store = ObjectStore('wa-opengraph')

print(":CouchDBComms: Attempting to construct class")
try:
    db = CouchDBComms('articles2')
    print("Successfully created class")
except:
    raise

#db.store_article({'url': 'http://www.google.com'})
