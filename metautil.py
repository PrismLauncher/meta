import json
from pprint import pprint
from jsonobject import *

'''
{
    "latest": {
        "release": "1.11.2",
        "snapshot": "17w06a"
    },
    "versions": [
        {
            "id": "17w06a",
            "releaseTime": "2017-02-08T13:16:29+00:00",
            "time": "2017-02-08T13:17:20+00:00",
            "type": "snapshot",
            "url": "https://launchermeta.mojang.com/mc/game/7db0c61afa278d016cf1dae2fba0146edfbf2f8e/17w06a.json"
        }
    ]
}
'''

class MojangIndexEntry(JsonObject):
    id = StringProperty()
    releaseTime = ISOTimestampProperty()
    time = ISOTimestampProperty()
    type = StringProperty()
    url = StringProperty()

class MojangIndex(JsonObject):
    latest = DictProperty(StringProperty)
    versions = ListProperty(MojangIndexEntry)

class MojangIndexWrap:
    def __init__(self, json):
        self.index = MojangIndex.wrap(json)
        self.latest = self.index.latest
        versionsDict = {}
        for version in self.index.versions:
            versionsDict[version.id] = version
        self.versions = versionsDict


class GradleSpecifier:
    'A gradle specifier - a maven coordinate'

    def __init__(self, name):
        components = name.split(':')
        self.group = components[0]
        self.artifact = components[1]
        self.version = components[2]
        if len(components) == 4:
            self.classifier = components[3]
        else:
            self.classifier = None

    def toString(self):
        if self.classifier:
            return "%s:%s:%s:%s" % (self.group, self.artifact, self.version, self.classifier)
        else:
            return "%s:%s:%s" % (self.group, self.artifact, self.version)

    def isLwjgl(self):
        return self.group in ("org.lwjgl.lwjgl", "net.java.jinput", "net.java.jutils")

class VersionPatch:
    'A version patch structure'

    def __init__(self, uid, name):
        self.uid = uid
        if name == None:
            self.name = self.uid
        else:
            self.name = name
        self.libraries = []
        self.version = None
        self.rules = []
        self.releaseType = None
        self.releaseTime = None

    def printout(self):
        print ("UID: " + self.uid)
        if self.name:
            print ("Name: " + self.name)
        if self.version:
            print ("Version: " + self.version)
        print ("Libraries:")
        pprint(self.libraries)
        print ("Rules:")
        pprint(self.rules)

    def write(self, filename):
        out = {}
        out["fileId"] = self.uid
        out["name"] = self.name

        if self.releaseTime:
            out["releaseTime"] = self.releaseTime.isoformat()

        if self.libraries and len(self.libraries) > 0:
            out["libraries"] = self.libraries

        if self.rules and len(self.rules) > 0:
            out["rules"] = self.rules

        if self.version:
            out["version"] = self.version

        if self.releaseType:
            out["type"] = "release"

        with open(filename, 'w') as outfile:
            json.dump(out, outfile, sort_keys=True, indent=4)
