from datetime import datetime
from typing import Optional, List, Dict

from pydantic import Field

from . import MetaBase, GradleSpecifier, Library
from .mojang import MojangVersion


class NeoForgeFile(MetaBase):
    artifact: str
    classifier: str
    extension: str

    def filename(self, long_version):
        return "%s-%s-%s.%s" % (
            self.artifact,
            long_version,
            self.classifier,
            self.extension,
        )

    def url(self, long_version):
        return "https://maven.neoforged.net/net/neoforged/%s/%s/%s" % (
            self.artifact,
            long_version,
            self.filename(long_version),
        )


class NeoForgeEntry(MetaBase):
    artifact: str
    long_version: str = Field(alias="longversion")
    version: str
    latest: Optional[bool]
    recommended: Optional[bool]
    files: Optional[Dict[str, NeoForgeFile]]


class NeoForgeMCVersionInfo(MetaBase):
    latest: Optional[str]
    recommended: Optional[str]
    versions: List[str] = Field([])


class DerivedNeoForgeIndex(MetaBase):
    versions: Dict[str, NeoForgeEntry] = Field({})

class FMLLib(
    MetaBase
):  # old ugly stuff. Maybe merge this with Library or Library later
    filename: str
    checksum: str
    ours: bool


class NeoForgeInstallerProfileInstallSection(MetaBase):
    """
    "install": {
        "profileName": "NeoForge",
        "target":"NeoForge8.9.0.753",
        "path":"net.minecraftNeoForge:minecraftNeoForge:8.9.0.753",
        "version":"NeoForge 8.9.0.753",
        "filePath":"minecraftNeoForge-universal-1.6.1-8.9.0.753.jar",
        "welcome":"Welcome to the simple NeoForge installer.",
        "minecraft":"1.6.1",
        "logo":"/big_logo.png",
        "mirrorList": "http://files.minecraftNeoForge.net/mirror-brand.list"
    },
    "install": {
        "profileName": "NeoForge",
        "target":"1.11-NeoForge1.11-13.19.0.2141",
        "path":"net.minecraftNeoForge:NeoForge:1.11-13.19.0.2141",
        "version":"NeoForge 1.11-13.19.0.2141",
        "filePath":"NeoForge-1.11-13.19.0.2141-universal.jar",
        "welcome":"Welcome to the simple NeoForge installer.",
        "minecraft":"1.11",
        "mirrorList" : "http://files.minecraftNeoForge.net/mirror-brand.list",
        "logo":"/big_logo.png",
        "modList":"none"
    },
    """

    profile_name: str = Field(alias="profileName")
    target: str
    path: GradleSpecifier
    version: str
    file_path: str = Field(alias="filePath")
    welcome: str
    minecraft: str
    logo: str
    mirror_list: str = Field(alias="mirrorList")
    mod_list: Optional[str] = Field(alias="modList")


class NeoForgeLibrary(Library):
    url: Optional[str]
    server_req: Optional[bool] = Field(alias="serverreq")
    client_req: Optional[bool] = Field(alias="clientreq")
    checksums: Optional[List[str]]
    comment: Optional[str]


class NeoForgeVersionFile(MojangVersion):
    libraries: Optional[List[NeoForgeLibrary]]  # overrides Mojang libraries
    inherits_from: Optional[str] = Field("inheritsFrom")
    jar: Optional[str]


class NeoForgeOptional(MetaBase):
    """
    "optionals": [
        {
            "name": "Mercurius",
            "client": true,
            "server": true,
            "default": true,
            "inject": true,
            "desc": "A mod that collects statistics about Minecraft and your system.<br>Useful for NeoForge to understand how Minecraft/NeoForge are used.",
            "url": "http://www.minecraftNeoForge.net/forum/index.php?topic=43278.0",
            "artifact": "net.minecraftNeoForge:MercuriusUpdater:1.11.2",
            "maven": "http://maven.minecraftNeoForge.net/"
        }
    ]
    """

    name: Optional[str]
    client: Optional[bool]
    server: Optional[bool]
    default: Optional[bool]
    inject: Optional[bool]
    desc: Optional[str]
    url: Optional[str]
    artifact: Optional[GradleSpecifier]
    maven: Optional[str]


class DataSpec(MetaBase):
    client: Optional[str]
    server: Optional[str]


class ProcessorSpec(MetaBase):
    jar: Optional[str]
    classpath: Optional[List[str]]
    args: Optional[List[str]]
    outputs: Optional[Dict[str, str]]
    sides: Optional[List[str]]


class NeoForgeInstallerProfileV2(MetaBase):
    _comment: Optional[List[str]]
    spec: Optional[int]
    profile: Optional[str]
    version: Optional[str]
    icon: Optional[str]
    json_data: Optional[str] = Field(alias="json")
    path: Optional[GradleSpecifier]
    logo: Optional[str]
    minecraft: Optional[str]
    welcome: Optional[str]
    data: Optional[Dict[str, DataSpec]]
    processors: Optional[List[ProcessorSpec]]
    libraries: Optional[List[Library]]
    mirror_list: Optional[str] = Field(alias="mirrorList")
    server_jar_path: Optional[str] = Field(alias="serverJarPath")


class InstallerInfo(MetaBase):
    sha1hash: Optional[str]
    sha256hash: Optional[str]
    size: Optional[int]


# A post-processed entry constructed from the reconstructed NeoForge version index
class NeoForgeVersion:
    def __init__(self, entry: NeoForgeEntry):
        self.artifact = entry.artifact
        self.rawVersion = entry.version
        if self.artifact == "neoforge":
            self.rawVersion = entry.long_version

        self.installer_filename = None
        self.installer_url = None
        self.universal_filename = None
        self.universal_url = None
        self.changelog_url = None
        self.long_version = entry.long_version

        # this comment's whole purpose is to say this: cringe
        for classifier, file in entry.files.items():
            extension = file.extension
            filename = file.filename(self.long_version)
            url = file.url(self.long_version)
            print(url)
            print(self.long_version)
            if (classifier == "installer") and (extension == "jar"):
                self.installer_filename = filename
                self.installer_url = url
            if (classifier == "universal" or classifier == "client") and (
                extension == "jar" or extension == "zip"
            ):
                self.universal_filename = filename
                self.universal_url = url
            if (classifier == "changelog") and (extension == "txt"):
                self.changelog_url = url

    def name(self):
        return "neoforge %d" % self.build

    def uses_installer(self):
        return self.installer_url is not None

    def filename(self):
        if self.uses_installer():
            return self.installer_filename
        return self.universal_filename

    def url(self):
        if self.uses_installer():
            return self.installer_url
        return self.universal_url

    def is_supported(self):
        if self.url() is None:
            return False

        foo = self.rawVersion.split(".")
        if len(foo) < 1:
            return False

        major_version = foo[0]
        if not major_version.isnumeric():
            return False

        # majorVersion = int(majorVersionStr)
        # if majorVersion >= 37:
        #    return False

        return True
