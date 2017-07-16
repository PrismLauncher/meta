#!/usr/bin/python3
'''
 Get the source files necessary for generating Forge versions
'''
from __future__ import print_function
import sys

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

import json
from jsonobject import *
from liteloaderutil import *
import os.path
import copy

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

forever_cache = FileCache('http_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)


# get the remote version list
r = sess.get('http://dl.liteloader.com/versions/versions.json')
r.raise_for_status()

# make sure it's JSON
main_json = r.json()

# make sure we understand the schema
remoteVersionlist = LiteloaderIndex(copy.deepcopy(main_json))
newStr = json.dumps(remoteVersionlist.to_json())
origStr = json.dumps(main_json)
assert newStr == origStr

# save the json it to file
with open("upstream/liteloader/versions.json", 'w', encoding='utf-8') as f:
    json.dump(main_json, f, sort_keys=True, indent=4)
