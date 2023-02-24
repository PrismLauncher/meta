def download_binary_file(sess, path, url):
    with open(path, "wb") as f:
        r = sess.get(url)
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=128):
            f.write(chunk)
