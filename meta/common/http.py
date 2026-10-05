import os

import requests

DOWNLOAD_ATTEMPTS = 3


def download_binary_file(sess, path, url):
    for attempt in range(DOWNLOAD_ATTEMPTS):
        try:
            with sess.get(url, stream=True) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=128):
                        f.write(chunk)
            return
        except (requests.ConnectionError, requests.exceptions.ChunkedEncodingError):
            if attempt == DOWNLOAD_ATTEMPTS - 1:
                raise
