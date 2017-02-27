import json
from pprint import pprint

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
