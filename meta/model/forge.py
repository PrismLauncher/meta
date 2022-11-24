from datetime import datetime
from typing import Optional, List, Dict

from pydantic import Field

from . import MetaBase, GradleSpecifier, MojangLibrary
from .mojang import MojangVersion


class ForgeFile(MetaBase):
    classifier: str
    hash: str
    extension: str

    def filename(self, long_version):
        return "%s-%s-%s.%s" % ("forge", long_version, self.classifier, self.extension)

    def url(self, long_version):
        return "https://maven.minecraftforge.net/net/minecraftforge/forge/%s/%s" % (
            long_version, self.filename(long_version))


class ForgeEntry(MetaBase):
    long_version: str = Field(alias="longversion")
    mc_version: str = Field(alias="mcversion")
    version: str
    build: int
    branch: Optional[str]
    latest: Optional[bool]
    recommended: Optional[bool]
    files: Optional[Dict[str, ForgeFile]]


class ForgeMCVersionInfo(MetaBase):
    latest: Optional[str]
    recommended: Optional[str]
    versions: List[str] = Field([])


class DerivedForgeIndex(MetaBase):
    versions: Dict[str, ForgeEntry] = Field({})
    by_mc_version: Dict[str, ForgeMCVersionInfo] = Field({}, alias="by_mcversion")


class FMLLib(MetaBase):  # old ugly stuff. Maybe merge this with Library or MojangLibrary later
    filename: str
    checksum: str
    ours: bool


class ForgeInstallerProfileInstallSection(MetaBase):
    """
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


class ForgeLibrary(MojangLibrary):
    url: Optional[str]
    server_req: Optional[bool] = Field(alias="serverreq")
    client_req: Optional[bool] = Field(alias="clientreq")
    checksums: Optional[List[str]]
    comment: Optional[str]


class ForgeVersionFile(MojangVersion):
    libraries: Optional[List[ForgeLibrary]]  # overrides Mojang libraries
    inherits_from: Optional[str] = Field("inheritsFrom")
    jar: Optional[str]


class ForgeOptional(MetaBase):
    """
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
            "maven": "http://maven.minecraftforge.net/"
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


class ForgeInstallerProfile(MetaBase):
    install: ForgeInstallerProfileInstallSection
    version_info: ForgeVersionFile = Field(alias="versionInfo")
    optionals: Optional[List[ForgeOptional]]


class ForgeLegacyInfo(MetaBase):
    release_time: Optional[datetime] = Field(alias="releaseTime")
    size: Optional[int]
    sha256: Optional[str]
    sha1: Optional[str]


class ForgeLegacyInfoList(MetaBase):
    number: Dict[str, ForgeLegacyInfo] = Field({})


class DataSpec(MetaBase):
    client: Optional[str]
    server: Optional[str]


class ProcessorSpec(MetaBase):
    jar: Optional[str]
    classpath: Optional[List[str]]
    args: Optional[List[str]]
    outputs: Optional[Dict[str, str]]
    sides: Optional[List[str]]


class ForgeInstallerProfileV2(MetaBase):
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
    libraries: Optional[List[MojangLibrary]]
    mirror_list: Optional[str] = Field(alias="mirrorList")
    server_jar_path: Optional[str] = Field(alias="serverJarPath")


class InstallerInfo(MetaBase):
    sha1hash: Optional[str]
    sha256hash: Optional[str]
    size: Optional[int]


# A post-processed entry constructed from the reconstructed Forge version index
class ForgeVersion:
    def __init__(self, entry: ForgeEntry):
        self.build = entry.build
        self.rawVersion = entry.version
        self.mc_version = entry.mc_version
        self.mc_version_sane = self.mc_version.replace("_pre", "-pre", 1)
        self.branch = entry.branch
        self.installer_filename = None
        self.installer_url = None
        self.universal_filename = None
        self.universal_url = None
        self.changelog_url = None
        self.long_version = "%s-%s" % (self.mc_version, self.rawVersion)
        if self.branch is not None:
            self.long_version += "-%s" % self.branch

        # this comment's whole purpose is to say this: cringe
        for classifier, file in entry.files.items():
            extension = file.extension
            filename = file.filename(self.long_version)
            url = file.url(self.long_version)
            if (classifier == "installer") and (extension == "jar"):
                self.installer_filename = filename
                self.installer_url = url
            if (classifier == "universal" or classifier == "client") and (extension == "jar" or extension == "zip"):
                self.universal_filename = filename
                self.universal_url = url
            if (classifier == "changelog") and (extension == "txt"):
                self.changelog_url = url

    def name(self):
        return "Forge %d" % self.build

    def uses_installer(self):
        if self.installer_url is None:
            return False
        if self.mc_version == "1.5.2":
            return False
        return True

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

        foo = self.rawVersion.split('.')
        if len(foo) < 1:
            return False

        major_version = foo[0]
        if not major_version.isnumeric():
            return False

        # majorVersion = int(majorVersionStr)
        # if majorVersion >= 37:
        #    return False

        return True


def fml_libs_for_version(mc_version: str) -> List[FMLLib]:
    argo_2_25 = FMLLib(filename="argo-2.25.jar",
                       checksum="bb672829fde76cb163004752b86b0484bd0a7f4b",
                       ours=False)
    argo_small_3_2 = FMLLib(filename="argo-small-3.2.jar",
                            checksum="58912ea2858d168c50781f956fa5b59f0f7c6b51",
                            ours=False)
    guava_12_0_1 = FMLLib(filename="guava-12.0.1.jar",
                          checksum="b8e78b9af7bf45900e14c6f958486b6ca682195f",
                          ours=False)
    guava_14_0_rc3 = FMLLib(filename="guava-14.0-rc3.jar",
                            checksum="931ae21fa8014c3ce686aaa621eae565fefb1a6a",
                            ours=False)
    asm_all_4_0 = FMLLib(filename="asm-all-4.0.jar",
                         checksum="98308890597acb64047f7e896638e0d98753ae82",
                         ours=False)
    asm_all_4_1 = FMLLib(filename="asm-all-4.1.jar",
                         checksum="054986e962b88d8660ae4566475658469595ef58",
                         ours=False)
    bcprov_jdk15on_147 = FMLLib(filename="bcprov-jdk15on-147.jar",
                                checksum="b6f5d9926b0afbde9f4dbe3db88c5247be7794bb",
                                ours=False)
    bcprov_jdk15on_148 = FMLLib(filename="bcprov-jdk15on-148.jar",
                                checksum="960dea7c9181ba0b17e8bab0c06a43f0a5f04e65",
                                ours=True)
    scala_library = FMLLib(filename="scala-library.jar",
                           checksum="458d046151ad179c85429ed7420ffb1eaf6ddf85",
                           ours=True)

    deobfuscation_data_1_5 = FMLLib(filename="deobfuscation_data_1.5.zip",
                                    checksum="5f7c142d53776f16304c0bbe10542014abad6af8",
                                    ours=False)

    deobfuscation_data_1_5_1 = FMLLib(filename="deobfuscation_data_1.5.1.zip",
                                      checksum="22e221a0d89516c1f721d6cab056a7e37471d0a6",
                                      ours=False)
    deobfuscation_data_1_5_2 = FMLLib(filename="deobfuscation_data_1.5.2.zip",
                                      checksum="446e55cd986582c70fcf12cb27bc00114c5adfd9",
                                      ours=False)
    if mc_version == "1.3.2":
        return [argo_2_25, guava_12_0_1, asm_all_4_0]
    elif mc_version in ["1.4", "1.4.1", "1.4.2", "1.4.3", "1.4.4", "1.4.5", "1.4.6", "1.4.7"]:
        return [argo_2_25, guava_12_0_1, asm_all_4_0, bcprov_jdk15on_147]
    elif mc_version == "1.5":
        return [argo_small_3_2, guava_14_0_rc3, asm_all_4_1, bcprov_jdk15on_148, deobfuscation_data_1_5,
                scala_library]
    elif mc_version == "1.5.1":
        return [argo_small_3_2, guava_14_0_rc3, asm_all_4_1, bcprov_jdk15on_148, deobfuscation_data_1_5_1,
                scala_library]
    elif mc_version == "1.5.2":
        return [argo_small_3_2, guava_14_0_rc3, asm_all_4_1, bcprov_jdk15on_148, deobfuscation_data_1_5_2,
                scala_library]
    return []
