from metautil import *
from collections import namedtuple

# A post-processed entry constructed from the reconstructed Forge version index
class ForgeVersion:
    def __init__(self, entry):
        self.build = entry.build
        self.rawVersion = entry.version
        self.mcversion = entry.mcversion
        self.mcversion_sane = self.mcversion.replace("_pre", "-pre", 1)
        self.branch = entry.branch
        self.installer_filename = None
        self.installer_url = None
        self.universal_filename = None
        self.universal_url = None
        self.changelog_url = None
        self.longVersion = "%s-%s" % (self.mcversion, self.rawVersion)
        if self.branch != None:
            self.longVersion = self.longVersion + "-%s" % (self.branch)
        for classifier, fileentry in entry.files.items():
            extension = fileentry.extension
            checksum = fileentry.hash
            filename = fileentry.filename(self.longVersion)
            url = fileentry.url(self.longVersion)
            if (classifier == "installer") and (extension == "jar"):
                self.installer_filename = filename
                self.installer_url = url
            if (classifier == "universal" or classifier == "client") and (extension == "jar" or extension == "zip"):
                self.universal_filename = filename
                self.universal_url = url
            if (classifier == "changelog") and (extension == "txt"):
                self.changelog_url = url

    def name(self):
        return "Forge %d" % (self.build)

    def usesInstaller(self):
        if self.installer_url == None:
            return False
        if self.mcversion == "1.5.2":
            return False
        return True

    def filename(self):
        if self.usesInstaller():
            return self.installer_filename
        else:
            return self.universal_filename

    def url(self):
        if self.usesInstaller():
            return self.installer_url
        else:
            return self.universal_url

    def isSupported(self):
        if self.url() == None:
            return False

        versionElements = self.rawVersion.split('.')
        if len(versionElements) < 1:
            return False

        majorVersionStr = versionElements[0]
        if not majorVersionStr.isnumeric():
            return False

        majorVersion = int(majorVersionStr)
        if majorVersion >= 37:
            return False

        return True

class ForgeFile(JsonObject):
    classifier = StringProperty(required=True)
    hash = StringProperty(required=True)
    extension = StringProperty(required=True)

    def filename(self, longversion):
        return "%s-%s-%s.%s" % ("forge", longversion, self.classifier, self.extension)

    def url(self, longversion):
        return "https://files.minecraftforge.net/maven/net/minecraftforge/forge/%s/%s" % (longversion, self.filename(longversion))

class ForgeEntry(JsonObject):
    longversion = StringProperty(required=True)
    mcversion = StringProperty(required=True)
    version = StringProperty(required=True)
    build = IntegerProperty(required=True)
    branch = StringProperty()
    latest = BooleanProperty()
    recommended = BooleanProperty()
    files = DictProperty(ForgeFile)

class ForgeMcVersionInfo(JsonObject):
    latest = StringProperty()
    recommended = StringProperty()
    versions = ListProperty(StringProperty())

class DerivedForgeIndex(JsonObject):
    versions = DictProperty(ForgeEntry)
    by_mcversion = DictProperty(ForgeMcVersionInfo)

'''
FML library mappings - these are added to legacy Forge versions because Forge no longer can download these
by itself - the locations have changed and some of this has to be rehosted on MultiMC servers.
'''

FMLLib = namedtuple('FMLLib', ('filename', 'checksum', 'ours'))

fmlLibsMapping = {}

fmlLibsMapping["1.3.2"] = [
    FMLLib("argo-2.25.jar", "bb672829fde76cb163004752b86b0484bd0a7f4b", False),
    FMLLib("guava-12.0.1.jar", "b8e78b9af7bf45900e14c6f958486b6ca682195f", False),
    FMLLib("asm-all-4.0.jar", "98308890597acb64047f7e896638e0d98753ae82", False)
]

fml14 = [
    FMLLib("argo-2.25.jar", "bb672829fde76cb163004752b86b0484bd0a7f4b", False),
    FMLLib("guava-12.0.1.jar", "b8e78b9af7bf45900e14c6f958486b6ca682195f", False),
    FMLLib("asm-all-4.0.jar", "98308890597acb64047f7e896638e0d98753ae82", False),
    FMLLib("bcprov-jdk15on-147.jar", "b6f5d9926b0afbde9f4dbe3db88c5247be7794bb", False)
]
fmlLibsMapping["1.4"] = fml14;
fmlLibsMapping["1.4.1"] = fml14;
fmlLibsMapping["1.4.2"] = fml14;
fmlLibsMapping["1.4.3"] = fml14;
fmlLibsMapping["1.4.4"] = fml14;
fmlLibsMapping["1.4.5"] = fml14;
fmlLibsMapping["1.4.6"] = fml14;
fmlLibsMapping["1.4.7"] = fml14;

fmlLibsMapping["1.5"] = [
    FMLLib("argo-small-3.2.jar", "58912ea2858d168c50781f956fa5b59f0f7c6b51", False),
    FMLLib("guava-14.0-rc3.jar", "931ae21fa8014c3ce686aaa621eae565fefb1a6a", False),
    FMLLib("asm-all-4.1.jar", "054986e962b88d8660ae4566475658469595ef58", False),
    FMLLib("bcprov-jdk15on-148.jar", "960dea7c9181ba0b17e8bab0c06a43f0a5f04e65", True),
    FMLLib("deobfuscation_data_1.5.zip", "5f7c142d53776f16304c0bbe10542014abad6af8", False),
    FMLLib("scala-library.jar", "458d046151ad179c85429ed7420ffb1eaf6ddf85", True)
]

fmlLibsMapping["1.5.1"] = [
    FMLLib("argo-small-3.2.jar", "58912ea2858d168c50781f956fa5b59f0f7c6b51", False),
    FMLLib("guava-14.0-rc3.jar", "931ae21fa8014c3ce686aaa621eae565fefb1a6a", False),
    FMLLib("asm-all-4.1.jar", "054986e962b88d8660ae4566475658469595ef58", False),
    FMLLib("bcprov-jdk15on-148.jar", "960dea7c9181ba0b17e8bab0c06a43f0a5f04e65", True),
    FMLLib("deobfuscation_data_1.5.1.zip", "22e221a0d89516c1f721d6cab056a7e37471d0a6", False),
    FMLLib("scala-library.jar", "458d046151ad179c85429ed7420ffb1eaf6ddf85", True)
]

fmlLibsMapping["1.5.2"] = [
    FMLLib("argo-small-3.2.jar", "58912ea2858d168c50781f956fa5b59f0f7c6b51", False),
    FMLLib("guava-14.0-rc3.jar", "931ae21fa8014c3ce686aaa621eae565fefb1a6a", False),
    FMLLib("asm-all-4.1.jar", "054986e962b88d8660ae4566475658469595ef58", False),
    FMLLib("bcprov-jdk15on-148.jar", "960dea7c9181ba0b17e8bab0c06a43f0a5f04e65", True),
    FMLLib("deobfuscation_data_1.5.2.zip", "446e55cd986582c70fcf12cb27bc00114c5adfd9", False),
    FMLLib("scala-library.jar", "458d046151ad179c85429ed7420ffb1eaf6ddf85", True)
]

'''
"install": {
    "profileName": "Forge",
    "target":"Forge8.9.0.753",
    "path":"net.minecraftforge:minecraftforge:8.9.0.753",
    "version":"Forge 8.9.0.753",
    "filePath":"minecraftforge-universal-1.6.1-8.9.0.753.jar",
    "welcome":"Welcome to the simple Forge installer.",
    "minecraft":"1.6.1",
    "logo":"/big_logo.png",
    "mirrorList": "http://files.minecraftforge.net/mirror-brand.list"
},
"install": {
    "profileName": "forge",
    "target":"1.11-forge1.11-13.19.0.2141",
    "path":"net.minecraftforge:forge:1.11-13.19.0.2141",
    "version":"forge 1.11-13.19.0.2141",
    "filePath":"forge-1.11-13.19.0.2141-universal.jar",
    "welcome":"Welcome to the simple forge installer.",
    "minecraft":"1.11",
    "mirrorList" : "http://files.minecraftforge.net/mirror-brand.list",
    "logo":"/big_logo.png",
    "modList":"none"
},
'''
class ForgeInstallerProfileInstallSection(JsonObject):
    profileName = StringProperty(required = True)
    target = StringProperty(required = True)
    path = GradleSpecifierProperty(required = True)
    version = StringProperty(required = True)
    filePath = StringProperty(required = True)
    welcome = StringProperty(required = True)
    minecraft = StringProperty(required = True)
    logo = StringProperty(required = True)
    mirrorList = StringProperty(required = True)
    modList = StringProperty(exclude_if_none=True, default=None)

class ForgeLibrary (MojangLibrary):
    url = StringProperty(exclude_if_none=True)
    serverreq = BooleanProperty(exclude_if_none=True, default=None)
    clientreq = BooleanProperty(exclude_if_none=True, default=None)
    checksums = ListProperty(StringProperty)
    comment = StringProperty()

class ForgeVersionFile (MojangVersionFile):
    libraries = ListProperty(ForgeLibrary, exclude_if_none=True, default=None) # overrides Mojang libraries
    inheritsFrom = StringProperty()
    jar = StringProperty()

'''
"optionals": [
    {
        "name": "Mercurius",
        "client": true,
        "server": true,
        "default": true,
        "inject": true,
        "desc": "A mod that collects statistics about Minecraft and your system.<br>Useful for Forge to understand how Minecraft/Forge are used.",
        "url": "http://www.minecraftforge.net/forum/index.php?topic=43278.0",
        "artifact": "net.minecraftforge:MercuriusUpdater:1.11.2",
        "maven": "http://files.minecraftforge.net/maven/"
    }
]
'''
class ForgeOptional (JsonObject):
    name = StringProperty()
    client = BooleanProperty()
    server = BooleanProperty()
    default = BooleanProperty()
    inject = BooleanProperty()
    desc = StringProperty()
    url = StringProperty()
    artifact = GradleSpecifierProperty()
    maven = StringProperty()

class ForgeInstallerProfile(JsonObject):
    install = ObjectProperty(ForgeInstallerProfileInstallSection, required = True)
    versionInfo = ObjectProperty(ForgeVersionFile, required = True)
    optionals = ListProperty(ForgeOptional)

class ForgeLegacyInfo(JsonObject):
    releaseTime = ISOTimestampProperty()
    size = IntegerProperty()
    sha256 = StringProperty()
    sha1 = StringProperty()

class ForgeLegacyInfoList(JsonObject):
    number = DictProperty(ForgeLegacyInfo)

class DataSpec(JsonObject):
    client = StringProperty()
    server = StringProperty()

class ProcessorSpec(JsonObject):
    jar = StringProperty()
    classpath = ListProperty(StringProperty)
    args = ListProperty(StringProperty)
    outputs = DictProperty(StringProperty)

# Note: This is only used in one version (1.12.2-14.23.5.2851) and we don't even use the installer profile in it.
#       It's here just so it parses and we can continue...
class ForgeInstallerProfileV1_5(JsonObject):
    _comment = ListProperty(StringProperty)
    spec = IntegerProperty()
    profile = StringProperty()
    version = StringProperty()
    icon = StringProperty()
    json = StringProperty()
    path = GradleSpecifierProperty()
    logo = StringProperty()
    minecraft = StringProperty()
    welcome = StringProperty()
    # We don't know what 'data' actually is in this one. It's an empty array
    data = ListProperty(StringProperty)
    processors = ListProperty(ProcessorSpec)
    libraries = ListProperty(MojangLibrary)
    mirrorList = StringProperty(exclude_if_none=True, default=None)

class ForgeInstallerProfileV2(JsonObject):
    _comment = ListProperty(StringProperty)
    spec = IntegerProperty()
    profile = StringProperty()
    version = StringProperty()
    icon = StringProperty()
    json = StringProperty()
    path = GradleSpecifierProperty()
    logo = StringProperty()
    minecraft = StringProperty()
    welcome = StringProperty()
    data = DictProperty(DataSpec)
    processors = ListProperty(ProcessorSpec)
    libraries = ListProperty(MojangLibrary)
    mirrorList = StringProperty(exclude_if_none=True, default=None)

class InstallerInfo(JsonObject):
    sha1hash = StringProperty()
    sha256hash = StringProperty()
    size = IntegerProperty()
