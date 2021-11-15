#!/usr/bin/python3
from __future__ import print_function
import sys
import os
import re
from metautil import *
from forgeutil import *
from jsonobject import *
from distutils.version import LooseVersion
from enum import Enum

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

#with open('multimc/index.json', 'r', encoding='utf-8') as index:
    #packages = MultiMCPackageIndex(json.load(index))

#for entry in packages.packages:
    #print (entry)

class DownloadType(Enum):
    NORMAL = 1
    FORGE_XZ = 2

class DownloadEntry:
    def __init__(self, url : str, kind : DownloadType, name : GradleSpecifier):
        self.name = name
        self.url = url
        self.kind = kind

    def __lt__(self, other):
        return self.name < other.name

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.name.__hash__()

    def toString(self):
        return "%s %s" % (self.name.toString(), self.url)

    def __repr__(self):
        return "DownloadEntry('" + self.toString() + "')"

class MojangLibrary (JsonObject):
    extract = ObjectProperty(MojangLibraryExtractRules, exclude_if_none=True, default=None)
    name = GradleSpecifierProperty(required = True)
    downloads = ObjectProperty(MojangLibraryDownloads, exclude_if_none=True, default=None)
    natives = DictProperty(StringProperty, exclude_if_none=True, default=None)
    rules = ListProperty(MojangRule, exclude_if_none=True, default=None)

class MultiMCLibrary (MojangLibrary):
    url = StringProperty(exclude_if_none=True, default=None)
    mmcHint = StringProperty(name="MMC-hint", exclude_if_none=True, default=None)


def GetLibraryDownload (library : MultiMCLibrary):
    if library.natives:
        raise Exception('Natives are not handled yet')

    name = library.name
    if library.mmcHint == 'forge-pack-xz':
        kind = DownloadType.FORGE_XZ
        name.extension = 'jar.pack.xz'
    else:
        kind = DownloadType.NORMAL

    if library.downloads:
        url = library.downloads.artifact.url
        if url.endswith('.zip'):
            name.extension = 'zip'


    if library.downloads:
        url = library.downloads.artifact.url
    else:
        if library.url:
            url = library.url + name.getPath()
        else:
            url = 'https://libraries.minecraft.net/' + name.getPath()

    return DownloadEntry(url, kind, name)

with open('multimc/net.minecraftforge/index.json', 'r', encoding='utf-8') as forgeIndex:
    forgeVersions = MultiMCVersionIndex(json.load(forgeIndex))

urlSet = set()

for entry in forgeVersions.versions:
    versionString = entry.version
    versionPath = "multimc/net.minecraftforge/%s.json" % versionString
    with open(versionPath, 'r') as infile:
        forgeVersion = MultiMCVersionFile(json.load(infile))
    if forgeVersion.libraries:
        for entry in forgeVersion.libraries:
            urlSet.add(GetLibraryDownload(entry))

    if forgeVersion.jarMods:
        for entry in forgeVersion.jarMods:
            urlSet.add(GetLibraryDownload(entry))

    if forgeVersion.mavenFiles:
        for entry in forgeVersion.mavenFiles:
            urlSet.add(GetLibraryDownload(entry))

forever_cache = FileCache('forge_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)

for entry in urlSet:
    libraryName = entry.name
    folderPath = "forgemaven/%s" % libraryName.getBase()
    filePath = "forgemaven/%s" % libraryName.getPath()
    if not os.path.isfile(filePath):
        os.makedirs(folderPath, exist_ok=True)
        rfile = sess.get(entry.url, stream=True)
        try:
            rfile.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            print('Missing: %s %s' % (entry.name, entry.url))
            continue
        print('Downloading %s' % entry.name)
        print('To %s' % filePath)
        with open(filePath, 'wb') as f:
            for chunk in rfile.iter_content(chunk_size=4096):
                f.write(chunk)
