def get_github_releases(sess, repo: str) -> list[dict]:
    releases = []
    page = 1
    while True:
        r = sess.get(
            f"https://api.github.com/repos/{repo}/releases",
            params={"per_page": 100, "page": page},
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        releases.extend(batch)
        page += 1
    return releases


def download_binary_file(sess, path, url):
    with open(path, "wb") as f:
        r = sess.get(url)
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=128):
            f.write(chunk)
