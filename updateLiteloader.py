import json
import os

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

from meta.common import upstream_path
from meta.common.liteloader import VERSIONS_FILE
from meta.model.liteloader import LiteloaderIndex

UPSTREAM_DIR = upstream_path()

forever_cache = FileCache('caches/http_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)


def main():
    # get the remote version list
    r = sess.get('http://dl.liteloader.com/versions/versions.json')
    r.raise_for_status()

    # make sure it's JSON
    main_json = r.json()

    # make sure we understand the schema
    remote_versions = LiteloaderIndex.parse_obj(main_json)
    parsed = remote_versions.json()
    original = json.dumps(main_json, sort_keys=True, indent=4)
    assert parsed == original

    print("Successfully parsed index")
    print(f"Last updated {remote_versions.meta.updated}")

    # save the json it to file
    remote_versions.write(os.path.join(UPSTREAM_DIR, VERSIONS_FILE))


if __name__ == '__main__':
    main()
