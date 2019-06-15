from metautil import *
import jsonobject

# barebones semver-like parser
def isFabricVerStable(ver):
    s = ver.split("+")
    return ("-" not in s[0])

class FabricInstallerArguments(JsonObject):
    client = ListProperty(StringProperty)
    common = ListProperty(StringProperty)
    server = ListProperty(StringProperty)

class FabricInstallerLaunchwrapper(JsonObject):
    tweakers = ObjectProperty(FabricInstallerArguments, required=True)

class FabricInstallerLibraries(JsonObject):
    client = ListProperty(MultiMCLibrary)
    common = ListProperty(MultiMCLibrary)
    server = ListProperty(MultiMCLibrary)

class FabricInstallerDataV1(JsonObject):
    version = IntegerProperty(required=True)
    libraries = ObjectProperty(FabricInstallerLibraries, required=True)
    mainClass = jsonobject.DefaultProperty()
    arguments = ObjectProperty(FabricInstallerArguments, required=False)
    launchwrapper = ObjectProperty(FabricInstallerLaunchwrapper, required=False)

class FabricJarInfo(JsonObject):
    releaseTime = ISOTimestampProperty()
    size = IntegerProperty()
    sha256 = StringProperty()
    sha1 = StringProperty()
