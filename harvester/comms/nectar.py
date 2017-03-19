#!/usr/bin/python3
"""comms.nectar

Classes used to programmatically use the NeCTAR Research Cloud.

boto.s3 docs: http://boto.cloudhackers.com/en/latest/ref/s3.html
"""

import requests

import boto.s3.connection
from boto.s3.key import Key

import core


class ObjectStore():

    def __init__(self, bucket_name):
        """"""
        args = core.config('nectar')
        self.bucket_name = bucket_name
        try:
            self.connection = boto.s3.connection.S3Connection(
                aws_access_key_id=args['ec2_access_key'],
                aws_secret_access_key=args['ec2_secret_key'],
                port=int(args['s3']['port']),
                host=args['s3']['host'],
                is_secure=True,
                validate_certs=False,
                calling_format=boto.s3.connection.OrdinaryCallingFormat()
            )
        except:
            raise
        # Open the bucket
        try:
            # get_bucket() requires validate=False to work with python3
            self.bucket = self.connection.get_bucket(
                self.bucket_name,
                validate=False
            )
        except:
            raise
        # Save the URL for public access
        self.public_url = args['s3']['public_url']

    def store(self, url):
        """Downloads a Web object from a specified URL and stores it in
        the NeCTAR Object Store. Returns the URL of the archived
        object.
        """
        try:
            response = requests.get(url)
            k = Key(self.bucket)
            k.set_contents_from_string(
                response.content,
                headers=response.headers
            )
            # Remove the double quotation marks from the k.etag string
            etag = k.etag[1:-1]
            # Return the URL of where the object should be stored
            object_url = '{public_url}{bucket}/{etag}'.format(
                public_url = self.public_url,
                bucket = self.bucket_name,
                etag = etag
            )
            return object_url
        except:
            raise
