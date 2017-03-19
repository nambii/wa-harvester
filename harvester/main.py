#!/usr/bin/python3
""""""

from flask import Flask

__author__ = "Elyas Khan"
__copyright__ = "Copyright 2016, The University of Melbourne"
__credits__ = ["Elyas Khan", "Yasmeen Mourice Samir George"]
__licence__ = "Proprietary"
__version__ = ""
__maintainer__ = "Elyas Khan"
__email__ = "elyas.khan@unimelb.edu.au"
__status__ = "Development"


app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"

if __name__ == "__main__":
    app.run()
