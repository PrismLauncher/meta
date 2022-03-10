import hashlib
import zipfile

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
from fabricutil import *

DATETIME_FORMAT_HTTP = "%a, %d %b %Y %H:%M:%S %Z"

UPSTREAM_DIR = os.environ["UPSTREAM_DIR"]

forever_cache = FileCache('caches/http_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)


def mkdirs(path):
    if not os.path.exists(path):
        os.makedirs(path)


def filehash(filename, hashtype, blocksize=65536):
    hash = hashtype()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()


def get_maven_url(mavenKey, server, ext):
    mavenParts = mavenKey.split(":", 3)
    mavenVerUrl = server + mavenParts[0].replace(".", "/") + "/" + mavenParts[1] + "/" + mavenParts[2] + "/"
    mavenUrl = mavenVerUrl + mavenParts[1] + "-" + mavenParts[2] + ext
    return mavenUrl


def get_json_file(path, url):
    with open(path, 'w', encoding='utf-8') as f:
        r = sess.get(url)
        r.raise_for_status()
        version_json = r.json()
        json.dump(version_json, f, sort_keys=True, indent=4)
        return version_json


def get_plaintext(url):
    r = sess.get(url)
    r.raise_for_status()
    return r.text


def head_file(url):
    r = sess.head(url)
    r.raise_for_status()
    return r.headers


def get_binary_file(path, url):
    with open(path, 'w', encoding='utf-8') as f:
        r = sess.get(url)
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=128):
                f.write(chunk)


def compute_jar_file(path, url):
    # These two approaches should result in the same metadata, except for the timestamp which might be a few minutes
    # off for the fallback method
    try:
        # Let's not download a Jar file if we don't need to.
        headers = head_file(url)
        tstamp = datetime.datetime.strptime(headers["Last-Modified"], DATETIME_FORMAT_HTTP)
        sha1 = get_plaintext(url + ".sha1")
        sha256 = get_plaintext(url + ".sha256")
        size = int(headers["Content-Length"])
    except requests.HTTPError:
        # Some older versions don't have a .sha256 file :(
        print(f"Falling back to downloading jar for {url}")

        jar_path = path + ".jar"
        get_binary_file(jar_path, url)
        tstamp = datetime.datetime.fromtimestamp(0)
        with zipfile.ZipFile(jar_path, 'r') as jar:
            allinfo = jar.infolist()
            for info in allinfo:
                tstamp_new = datetime.datetime(*info.date_time)
                if tstamp_new > tstamp:
                    tstamp = tstamp_new

        sha1 = filehash(jar_path, hashlib.sha1)
        sha256 = filehash(jar_path, hashlib.sha256)
        size = os.path.getsize(jar_path)

    data = FabricJarInfo()
    data.releaseTime = tstamp
    data.sha1 = sha1
    data.sha256 = sha256
    data.size = size
    with open(path + ".json", 'w') as outfile:
        json.dump(data.to_json(), outfile, sort_keys=True, indent=4)


mkdirs(UPSTREAM_DIR + "/fabric/meta-v2")
mkdirs(UPSTREAM_DIR + "/fabric/loader-installer-json")
mkdirs(UPSTREAM_DIR + "/fabric/jars")

# get the version list for each component we are interested in
for component in ["intermediary", "loader"]:
    index = get_json_file(UPSTREAM_DIR + "/fabric/meta-v2/" + component + ".json",
                          "https://meta.fabricmc.net/v2/versions/" + component)
    for it in index:
        jarMavenUrl = get_maven_url(it["maven"], "https://maven.fabricmc.net/", ".jar")
        compute_jar_file(UPSTREAM_DIR + "/fabric/jars/" + it["maven"].replace(":", "."), jarMavenUrl)

# for each loader, download installer JSON file from maven
with open(UPSTREAM_DIR + "/fabric/meta-v2/loader.json", 'r', encoding='utf-8') as loaderVersionIndexFile:
    loaderVersionIndex = json.load(loaderVersionIndexFile)
    for it in loaderVersionIndex:
        mavenUrl = get_maven_url(it["maven"], "https://maven.fabricmc.net/", ".json")
        get_json_file(UPSTREAM_DIR + "/fabric/loader-installer-json/" + it["version"] + ".json", mavenUrl)
