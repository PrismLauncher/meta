from metautil import *

'''
    "repo":{
        "stream":"RELEASE",
        "type":"m2",
        "url":"http:\/\/dl.liteloader.com\/repo\/",
        "classifier":""
    },
'''
class LiteloaderRepo(JsonObject):
    stream = StringProperty(required=True)
    type = StringProperty(required=True)
    url = StringProperty(required=True)
    classifier = StringProperty(required=True)

'''
    "53639d52340479ccf206a04f5e16606f":{
        "tweakClass":"com.mumfrey.liteloader.launch.LiteLoaderTweaker",
        "libraries":[
            {
                "name":"net.minecraft:launchwrapper:1.5"
            },
            {
                "name":"net.sf.jopt-simple:jopt-simple:4.5"
            },
            {
                "name":"org.ow2.asm:asm-all:4.1"
            }
        ],
        "stream":"RELEASE",
        "file":"liteloader-1.5.2_01.jar",
        "version":"1.5.2_01",
        "md5":"53639d52340479ccf206a04f5e16606f",
        "timestamp":"1367366420"
    },
'''
class LiteloaderArtefact(JsonObject):
    tweakClass = StringProperty(required=True)
    libraries = ListProperty(MultiMCLibrary, required=True)
    stream = StringProperty(required=True)
    file = StringProperty(required=True)
    version = StringProperty(required=True)
    build = StringProperty(default=None, exclude_if_none=True)
    md5 = StringProperty(required=True)
    timestamp = StringProperty(required=True)
    srcJar = StringProperty(default=None, exclude_if_none=True)
    mcpJar = StringProperty(default=None, exclude_if_none=True)

class LiteloaderDev(JsonObject):
    fgVersion = StringProperty(default=None ,exclude_if_none=True)
    mappings = StringProperty(required=None, exclude_if_none=True)
    mcp = StringProperty(default=None, exclude_if_none=True)

class LiteloaderArtefacts(JsonObject):
    liteloader = DictProperty(LiteloaderArtefact, name="com.mumfrey:liteloader", required=True)

class LiteloaderSnapshot(LiteloaderArtefact):
    lastSuccessfulBuild = IntegerProperty()

class LiteloaderSnapshots(JsonObject):
    libraries = ListProperty(MultiMCLibrary, required=True)
    liteloader = DictProperty(LiteloaderSnapshot, name="com.mumfrey:liteloader", required=True)

'''
    "1.10.2":{
        "dev": { ... },
        "repo":{ ... },
        "artefacts":{
            "com.mumfrey:liteloader":{ },
            ...
        },
        "snapshots":{
            ...
        }
'''
class LiteloaderEntry(JsonObject):
    dev = ObjectProperty(LiteloaderDev, default=None, exclude_if_none=True)
    repo = ObjectProperty(LiteloaderRepo, required=True)
    artefacts = ObjectProperty(LiteloaderArtefacts, default=None, exclude_if_none=True)
    snapshots = ObjectProperty(LiteloaderSnapshots, default=None, exclude_if_none=True)

'''
    "meta":{
        "description":"LiteLoader is a lightweight mod bootstrap designed to provide basic loader functionality for mods which don't need to modify game mechanics.",
        "authors":"Mumfrey",
        "url":"http:\/\/dl.liteloader.com",
        "updated":"2017-02-22T11:34:07+00:00",
        "updatedTime":1487763247
    },
'''
class LiteloaderMeta(JsonObject):
    description = StringProperty(required=True)
    authors = StringProperty(required=True)
    url = StringProperty(required=True)
    updated = ISOTimestampProperty(required=True)
    updatedTime = IntegerProperty(required=True)

# The raw Forge version index
class LiteloaderIndex(JsonObject):
    meta = ObjectProperty(LiteloaderMeta, required=True)
    versions = DictProperty(LiteloaderEntry)

