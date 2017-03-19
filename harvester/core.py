#!/usr/bin/python3
""""""

import os
import sys
import yaml
import argparse
from datetime import datetime
import dateutil.parser

def config(*subconfig):
    """Returns a dict that contains all of the settings.

    The settings are a combination of data in config.yaml and valid
    command line arguments.

    Args:
        *subconfig (str): Pass strings to return specific subsets of
            the config.

    Returns:
        dict: Software settings (config.yaml and command line args).

    Raises:

    """

    # Save current working dir
    cwd = os.getcwd()
    # Change working dir to the projects base dir
    current_dir = os.path.dirname(os.path.realpath(__file__))
    target_dir = os.path.dirname(current_dir)
    os.chdir(target_dir)
    # Parse config.yaml
    with open('config.yaml', 'r') as stream:
        args = yaml.load(stream)
    # Change working dir back to original dir
    os.chdir(cwd)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='')
    parser.add_argument(
        '--node',
        '-n',
        help='The node ID.'
    )
    parser.add_argument(
        '--processes',
        '-p',
        help='The total number of processes.'
    )
    # Store command line arguments in a dict
    cl_args = parser.parse_args()
    cl_args_dict = vars(cl_args)
    # Combine
    args.update(cl_args_dict)
    # Find subconfig if argument is passed
    for s in subconfig:
        try:
            args = args[s]
        except:
            pass
    # Return
    return args

def get_time(date):
    """A commonly used method to convert ISO 8601 datetimes to UNIX
    timestamps.
    """
    dt = dateutil.parser.parse(date)
    time = str(int(dt.timestamp()))
    return time

def dt():
    """
    """
    return datetime.now().strftime('[%d/%b/%Y %H:%M:%S] ')
