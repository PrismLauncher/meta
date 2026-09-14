import json
import os

from meta.common import upstream_path, ensure_upstream_dir, default_session
from meta.common.liteloader import VERSIONS_FILE, BASE_DIR
from meta.model.liteloader import LiteloaderIndex

UPSTREAM_DIR = upstream_path()

ensure_upstream_dir(BASE_DIR)

sess = default_session()


def main():
    # get the remote version list
    r = sess.get("http://dl.liteloader.com/versions/versions.json")
    r.raise_for_status()

    # make sure it's JSON
    main_json = r.json()

    # make sure we understand the schema
    remote_versions = LiteloaderIndex.model_validate(main_json)
    parsed = remote_versions.model_dump(mode="json", exclude_none=True, by_alias=True)
    assert parsed == main_json

    print("Successfully parsed index")
    print(f"Last updated {remote_versions.meta.updated}")

    # save the json it to file
    remote_versions.write(os.path.join(UPSTREAM_DIR, VERSIONS_FILE))


if __name__ == "__main__":
    main()
