from datetime import datetime
from typing import Optional, List, Dict, Any, Iterator
from .enum import StrEnum

from pydantic import validator, Field

from . import (
    MetaBase,
    MojangArtifactBase,
    MojangAssets,
    MojangArtifact,
    MojangLibraryDownloads,
    MojangLogging,
    Library,
    MetaVersion,
    GradleSpecifier,
)

SUPPORTED_LAUNCHER_VERSION = 21
SUPPORTED_COMPLIANCE_LEVEL = 1
DEFAULT_JAVA_MAJOR = 8  # By default, we should recommend Java 8 if we don't know better
DEFAULT_JAVA_NAME = (
    "jre-legacy"  # By default, we should recommend Java 8 if we don't know better
)
COMPATIBLE_JAVA_MAPPINGS = {16: [17]}
SUPPORTED_FEATURES = ["is_quick_play_multiplayer", "is_quick_play_singleplayer"]
MOJANG_VERSION_APRIL_2019_NON_STANDARD_FIX: Dict[str, Any] = {
    "+traits": [
        "FirstThreadOnMacOS"
    ],
    "assetIndex": {
        "id": "1.14-af",
        "sha1": "5c7028b2c197372b6b7570ead909515232a936ab",
        "size": 224712,
        "totalSize": 206652481,
        "url": "https://piston-meta.mojang.com/v1/packages/5c7028b2c197372b6b7570ead909515232a936ab/1.14-af.json"
    },
    "compatibleJavaMajors": [
        8
    ],
    "compatibleJavaName": "jre-legacy",
    "formatVersion": 1,
    "libraries": [
        {
            "downloads": {
                "artifact": {
                    "sha1": "eb8bb7b66fa0e2152b1b40b3856e82f7619439ee",
                    "size": 23581,
                    "url": "https://libraries.minecraft.net/com/mojang/patchy/1.3.9/patchy-1.3.9.jar"
                }
            },
            "name": "com.mojang:patchy:1.3.9"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "9ddf7b048a8d701be231c0f4f95fd986198fd2d8",
                    "size": 30973,
                    "url": "https://libraries.minecraft.net/oshi-project/oshi-core/1.1/oshi-core-1.1.jar"
                }
            },
            "name": "oshi-project:oshi-core:1.1"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "cb208278274bf12ebdb56c61bd7407e6f774d65a",
                    "size": 1091208,
                    "url": "https://libraries.minecraft.net/net/java/dev/jna/jna/4.4.0/jna-4.4.0.jar"
                }
            },
            "name": "net.java.dev.jna:jna:4.4.0"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "e3f70017be8100d3d6923f50b3d2ee17714e9c13",
                    "size": 913436,
                    "url": "https://libraries.minecraft.net/net/java/dev/jna/platform/3.4.0/platform-3.4.0.jar"
                }
            },
            "name": "net.java.dev.jna:platform:3.4.0"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "63d216a9311cca6be337c1e458e587f99d382b84",
                    "size": 1634692,
                    "url": "https://libraries.minecraft.net/com/ibm/icu/icu4j-core-mojang/51.2/icu4j-core-mojang-51.2.jar"
                }
            },
            "name": "com.ibm.icu:icu4j-core-mojang:51.2"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "6aa6453aa99a52a5cd91749da1af6ab70e082ab3",
                    "size": 5111,
                    "url": "https://libraries.minecraft.net/com/mojang/javabridge/1.0.22/javabridge-1.0.22.jar"
                }
            },
            "name": "com.mojang:javabridge:1.0.22"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "cdd846cfc4e0f7eefafc02c0f5dce32b9303aa2a",
                    "size": 78175,
                    "url": "https://libraries.minecraft.net/net/sf/jopt-simple/jopt-simple/5.0.3/jopt-simple-5.0.3.jar"
                }
            },
            "name": "net.sf.jopt-simple:jopt-simple:5.0.3"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "d0626cd3108294d1d58c05859add27b4ef21f83b",
                    "size": 3823147,
                    "url": "https://libraries.minecraft.net/io/netty/netty-all/4.1.25.Final/netty-all-4.1.25.Final.jar"
                }
            },
            "name": "io.netty:netty-all:4.1.25.Final"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "3a3d111be1be1b745edfa7d91678a12d7ed38709",
                    "size": 2521113,
                    "url": "https://libraries.minecraft.net/com/google/guava/guava/21.0/guava-21.0.jar"
                }
            },
            "name": "com.google.guava:guava:21.0"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "6c6c702c89bfff3cd9e80b04d668c5e190d588c6",
                    "size": 479881,
                    "url": "https://libraries.minecraft.net/org/apache/commons/commons-lang3/3.5/commons-lang3-3.5.jar"
                }
            },
            "name": "org.apache.commons:commons-lang3:3.5"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "2852e6e05fbb95076fc091f6d1780f1f8fe35e0f",
                    "size": 208700,
                    "url": "https://libraries.minecraft.net/commons-io/commons-io/2.5/commons-io-2.5.jar"
                }
            },
            "name": "commons-io:commons-io:2.5"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "4b95f4897fa13f2cd904aee711aeafc0c5295cd8",
                    "size": 284184,
                    "url": "https://libraries.minecraft.net/commons-codec/commons-codec/1.10/commons-codec-1.10.jar"
                }
            },
            "name": "commons-codec:commons-codec:1.10"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "c6b7dc51dd44379cc751b7504816006e9be4b1e6",
                    "size": 77392,
                    "url": "https://libraries.minecraft.net/com/mojang/brigadier/1.0.17/brigadier-1.0.17.jar"
                }
            },
            "name": "com.mojang:brigadier:1.0.17"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "dfd38f37b52df28f056726c765c547a42f966b0f",
                    "size": 437308,
                    "url": "https://libraries.minecraft.net/com/mojang/datafixerupper/2.0.23/datafixerupper-2.0.23.jar"
                }
            },
            "name": "com.mojang:datafixerupper:2.0.23"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "c4ba5371a29ac9b2ad6129b1d39ea38750043eff",
                    "size": 231952,
                    "url": "https://libraries.minecraft.net/com/google/code/gson/gson/2.8.0/gson-2.8.0.jar"
                }
            },
            "name": "com.google.code.gson:gson:2.8.0"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "9834cdf236c22e84b946bba989e2f94ef5897c3c",
                    "size": 65621,
                    "url": "https://libraries.minecraft.net/com/mojang/authlib/1.5.25/authlib-1.5.25.jar"
                }
            },
            "name": "com.mojang:authlib:1.5.25"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "a698750c16740fd5b3871425f4cb3bbaa87f529d",
                    "size": 365552,
                    "url": "https://libraries.minecraft.net/org/apache/commons/commons-compress/1.8.1/commons-compress-1.8.1.jar"
                }
            },
            "name": "org.apache.commons:commons-compress:1.8.1"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "18f4247ff4572a074444572cee34647c43e7c9c7",
                    "size": 589512,
                    "url": "https://libraries.minecraft.net/org/apache/httpcomponents/httpclient/4.3.3/httpclient-4.3.3.jar"
                }
            },
            "name": "org.apache.httpcomponents:httpclient:4.3.3"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "f6f66e966c70a83ffbdb6f17a0919eaf7c8aca7f",
                    "size": 62050,
                    "url": "https://libraries.minecraft.net/commons-logging/commons-logging/1.1.3/commons-logging-1.1.3.jar"
                }
            },
            "name": "commons-logging:commons-logging:1.1.3"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "31fbbff1ddbf98f3aa7377c94d33b0447c646b6e",
                    "size": 282269,
                    "url": "https://libraries.minecraft.net/org/apache/httpcomponents/httpcore/4.3.2/httpcore-4.3.2.jar"
                }
            },
            "name": "org.apache.httpcomponents:httpcore:4.3.2"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "5ad88f325e424f8dbc2be5459e21ea5cab3864e9",
                    "size": 18800417,
                    "url": "https://libraries.minecraft.net/it/unimi/dsi/fastutil/8.2.1/fastutil-8.2.1.jar"
                }
            },
            "name": "it.unimi.dsi:fastutil:8.2.1"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "d771af8e336e372fb5399c99edabe0919aeaf5b2",
                    "size": 301872,
                    "url": "https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-api/2.17.1/log4j-api-2.17.1.jar"
                }
            },
            "name": "org.apache.logging.log4j:log4j-api:2.17.1"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "779f60f3844dadc3ef597976fcb1e5127b1f343d",
                    "size": 1790452,
                    "url": "https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-core/2.17.1/log4j-core-2.17.1.jar"
                }
            },
            "name": "org.apache.logging.log4j:log4j-core:2.17.1"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "f581915be14fc38f6784a4f98209f2de5a9cc4d3",
                    "size": 6381195,
                    "url": "https://libraries.minecraft.net/com/mojang/realms/1.14.2/realms-1.14.2.jar"
                }
            },
            "name": "com.mojang:realms:1.14.2"
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "172fe3ccf0e7143cbbfba006554412c8e6fc81f2",
                    "size": 12952,
                    "url": "https://libraries.minecraft.net/com/mojang/text2speech/1.11.2/text2speech-1.11.2.jar"
                }
            },
            "name": "com.mojang:text2speech:1.11.2",
            "rules": [
                {
                    "action": "allow"
                },
                {
                    "action": "disallow",
                    "os": {
                        "name": "osx-arm64"
                    }
                }
            ]
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "6ef160c3133a78de015830860197602ca1c855d3",
                    "size": 40502,
                    "url": "https://libraries.minecraft.net/ca/weblite/java-objc-bridge/1.0.0/java-objc-bridge-1.0.0.jar"
                },
                "classifiers": {
                    "natives-osx": {
                        "sha1": "08befab4894d55875f33c3d300f4f71e6e828f64",
                        "size": 5629,
                        "url": "https://libraries.minecraft.net/ca/weblite/java-objc-bridge/1.0.0/java-objc-bridge-1.0.0-natives-osx.jar"
                    }
                }
            },
            "extract": {
                "exclude": [
                    "META-INF/"
                ]
            },
            "name": "ca.weblite:java-objc-bridge:1.0.0",
            "natives": {
                "osx": "natives-osx"
            },
            "rules": [
                {
                    "action": "allow",
                    "os": {
                        "name": "osx"
                    }
                }
            ]
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "f378f889797edd7df8d32272c06ca80a1b6b0f58",
                    "size": 13164,
                    "url": "https://libraries.minecraft.net/com/mojang/text2speech/1.11.3/text2speech-1.11.3.jar"
                }
            },
            "name": "com.mojang:text2speech:1.11.3",
            "rules": [
                {
                    "action": "allow",
                    "os": {
                        "name": "osx-arm64"
                    }
                }
            ]
        },
        {
            "downloads": {
                "artifact": {
                    "sha1": "369a83621e3c65496348491e533cb97fe5f2f37d",
                    "size": 91947,
                    "url": "https://github.com/MinecraftMachina/Java-Objective-C-Bridge/releases/download/1.1.0-mmachina.1/java-objc-bridge-1.1.jar"
                }
            },
            "name": "ca.weblite:java-objc-bridge:1.1.0-mmachina.1",
            "rules": [
                {
                    "action": "allow",
                    "os": {
                        "name": "osx-arm64"
                    }
                }
            ]
        }
    ],
    "logging": {
        "argument": "-Dlog4j.configurationFile=${path}",
        "file": {
            "id": "client-1.12.xml",
            "sha1": "bd65e7d2e3c237be76cfbef4c2405033d7f91521",
            "size": 888,
            "url": "https://piston-data.mojang.com/v1/objects/bd65e7d2e3c237be76cfbef4c2405033d7f91521/client-1.12.xml"
        },
        "type": "log4j2-xml"
    },
    "mainClass": "net.minecraft.client.main.Main",
    "mainJar": {
        "downloads": {
            "artifact": {
                "sha1": "44db7d7bcd5a1bee6f54f6a623f26a1b3d1e293f",
                "size": 18879423,
                "url": "https://piston-data.mojang.com/v1/objects/44db7d7bcd5a1bee6f54f6a623f26a1b3d1e293f/client.jar"
            }
        },
        "name": "com.mojang:minecraft:3dshareware-1.34:client"
    },
    "minecraftArguments": "--username ${auth_player_name} --version ${version_name} --gameDir ${game_directory} --assetsDir ${assets_root} --assetIndex ${assets_index_name} --uuid ${auth_uuid} --accessToken ${auth_access_token} --userType ${user_type} --versionType ${version_type}",
    "name": "Minecraft",
    "order": -2,
    "releaseTime": "2019-04-01T11:18:08+00:00",
    "requires": [
        {
            "suggests": "3.2.1",
            "uid": "org.lwjgl3"
        }
    ],
    "type": "snapshot",
    "uid": "net.minecraft",
    "version": "3D Shareware v1.34"
}

"""
Mojang index files look like this:
{
    "latest": {
        "release": "1.11.2",
        "snapshot": "17w06a"
    },
    "versions": [
        ...
        {
            "id": "17w06a",
            "releaseTime": "2017-02-08T13:16:29+00:00",
            "time": "2017-02-08T13:17:20+00:00",
            "type": "snapshot",
            "url": "https://launchermeta.mojang.com/mc/game/7db0c61afa278d016cf1dae2fba0146edfbf2f8e/17w06a.json"
        },
        ...
    ]
}
"""


class MojangLatestVersion(MetaBase):
    release: str
    snapshot: str


class MojangIndexEntry(MetaBase):
    id: Optional[str]
    release_time: Optional[datetime] = Field(alias="releaseTime")
    time: Optional[datetime]
    type: Optional[str]
    url: Optional[str]
    sha1: Optional[str]
    compliance_level: Optional[int] = Field(alias="complianceLevel")


class MojangIndex(MetaBase):
    latest: MojangLatestVersion
    versions: List[MojangIndexEntry]


class MojangIndexWrap:
    def __init__(self, index: MojangIndex):
        self.index = index
        self.latest = index.latest
        self.versions = dict((x.id, x) for x in index.versions)


class ExperimentEntry(MetaBase):
    id: str
    url: str
    wiki: Optional[str]


class ExperimentIndex(MetaBase):
    experiments: List[ExperimentEntry]


class ExperimentIndexWrap:
    def __init__(self, index: ExperimentIndex):
        self.index: ExperimentIndex = index
        self.versions: Dict[str, ExperimentEntry] = dict(
            (x.id, x) for x in index.experiments
        )


class OldSnapshotEntry(MetaBase):
    id: str
    url: str
    wiki: Optional[str]
    jar: str
    sha1: str
    size: int


class OldSnapshotIndex(MetaBase):
    old_snapshots: List[OldSnapshotEntry]


class OldSnapshotIndexWrap:
    def __init__(self, index: OldSnapshotIndex):
        self.index: OldSnapshotIndex = index
        self.versions: Dict[str, OldSnapshotEntry] = dict(
            (x.id, x) for x in index.old_snapshots
        )


class LegacyOverrideEntry(MetaBase):
    main_class: Optional[str] = Field(alias="mainClass")
    applet_class: Optional[str] = Field(alias="appletClass")
    release_time: Optional[datetime] = Field(alias="releaseTime")
    additional_traits: Optional[List[str]] = Field(alias="+traits")
    additional_jvm_args: Optional[List[str]] = Field(alias="+jvmArgs")

    def apply_onto_meta_version(self, meta_version: MetaVersion, legacy: bool = True):
        # simply hard override classes
        meta_version.main_class = self.main_class
        meta_version.applet_class = self.applet_class
        # if we have an updated release time (more correct than Mojang), use it
        if self.release_time:
            meta_version.release_time = self.release_time

        # add traits, if any
        if self.additional_traits:
            if not meta_version.additional_traits:
                meta_version.additional_traits = []
            meta_version.additional_traits += self.additional_traits

        if self.additional_jvm_args:
            if not meta_version.additional_jvm_args:
                meta_version.additional_jvm_args = []
            meta_version.additional_jvm_args += self.additional_jvm_args

        if legacy:
            # remove all libraries - they are not needed for legacy
            meta_version.libraries = None


class LegacyOverrideIndex(MetaBase):
    versions: Dict[str, LegacyOverrideEntry]


class LibraryPatch(MetaBase):
    match: List[GradleSpecifier]
    override: Optional[Library]
    additionalLibraries: Optional[List[Library]]
    patchAdditionalLibraries: bool = Field(False)

    def applies(self, target: Library) -> bool:
        return target.name in self.match


class LibraryPatches(MetaBase):
    __root__: List[LibraryPatch]

    def __iter__(self) -> Iterator[LibraryPatch]:
        return iter(self.__root__)

    def __getitem__(self, item) -> LibraryPatch:
        return self.__root__[item]


class LegacyServices(MetaBase):
    __root__: List[str]

    def __iter__(self) -> Iterator[str]:
        return iter(self.__root__)

    def __getitem__(self, item) -> str:
        return self.__root__[item]


class MojangArguments(MetaBase):
    game: Optional[List[Any]]  # mixture of strings and objects
    jvm: Optional[List[Any]]


class MojangJavaComponent(StrEnum):
    JreLegacy = "jre-legacy"
    Alpha = "java-runtime-alpha"
    Beta = "java-runtime-beta"
    Gamma = "java-runtime-gamma"
    GammaSnapshot = "java-runtime-gamma-snapshot"
    Exe = "minecraft-java-exe"
    Delta = "java-runtime-delta"


class JavaVersion(MetaBase):
    component: MojangJavaComponent = MojangJavaComponent.JreLegacy
    major_version: int = Field(8, alias="majorVersion")


class MojangJavaIndexAvailability(MetaBase):
    group: int
    progress: int


class MojangJavaIndexManifest(MetaBase):
    sha1: str
    size: int
    url: str


class MojangJavaIndexVersion(MetaBase):
    name: str
    released: datetime


class MojangJavaRuntime(MetaBase):
    availability: MojangJavaIndexAvailability
    manifest: MojangJavaIndexManifest
    version: MojangJavaIndexVersion


class MojangJavaIndexEntry(MetaBase):
    __root__: dict[MojangJavaComponent, list[MojangJavaRuntime]]

    def __iter__(self) -> Iterator[MojangJavaComponent]:
        return iter(self.__root__)

    def __getitem__(self, item) -> list[MojangJavaRuntime]:
        return self.__root__[item]


class MojangJavaOsName(StrEnum):
    Gamecore = "gamecore"
    Linux = "linux"
    Linuxi386 = "linux-i386"
    MacOs = "mac-os"
    MacOSArm64 = "mac-os-arm64"
    WindowsArm64 = "windows-arm64"
    WindowsX64 = "windows-x64"
    WindowsX86 = "windows-x86"


class JavaIndex(MetaBase):
    __root__: dict[MojangJavaOsName, MojangJavaIndexEntry]

    def __iter__(self) -> Iterator[MojangJavaOsName]:
        return iter(self.__root__)

    def __getitem__(self, item) -> MojangJavaIndexEntry:
        return self.__root__[item]


class MojangVersion(MetaBase):
    @validator("minimum_launcher_version")
    def validate_minimum_launcher_version(cls, v):
        assert v <= SUPPORTED_LAUNCHER_VERSION
        return v

    @validator("compliance_level")
    def validate_compliance_level(cls, v):
        assert v <= SUPPORTED_COMPLIANCE_LEVEL
        return v

    id: str  # TODO: optional?
    arguments: Optional[MojangArguments]
    asset_index: Optional[MojangAssets] = Field(alias="assetIndex")
    assets: Optional[str]
    downloads: Optional[Dict[str, MojangArtifactBase]]  # TODO improve this?
    libraries: Optional[List[Library]]  # TODO: optional?
    main_class: Optional[str] = Field(alias="mainClass")
    applet_class: Optional[str] = Field(alias="appletClass")
    processArguments: Optional[str]
    minecraft_arguments: Optional[str] = Field(alias="minecraftArguments")
    minimum_launcher_version: Optional[int] = Field(alias="minimumLauncherVersion")
    release_time: Optional[datetime] = Field(alias="releaseTime")
    time: Optional[datetime]
    type: Optional[str]
    inherits_from: Optional[str] = Field("inheritsFrom")
    logging: Optional[Dict[str, MojangLogging]]  # TODO improve this?
    compliance_level: Optional[int] = Field(alias="complianceLevel")
    javaVersion: Optional[JavaVersion]

    def to_meta_version(self, name: str, uid: str, version: str) -> MetaVersion:
        main_jar = None
        addn_traits = None
        new_type = self.type
        compatible_java_majors = None
        if self.id:
            client_download = self.downloads["client"]
            artifact = MojangArtifact(
                url=client_download.url,
                sha1=client_download.sha1,
                size=client_download.size,
            )
            downloads = MojangLibraryDownloads(artifact=artifact)
            main_jar = Library(
                name=GradleSpecifier("com.mojang", "minecraft", self.id, "client"),
                downloads=downloads,
            )

        if not self.compliance_level:  # both == 0 and is None
            pass
        elif self.compliance_level == 1:
            if not addn_traits:
                addn_traits = []
            addn_traits.append("XR:Initial")
        else:
            raise Exception(f"Unsupported compliance level {self.compliance_level}")

        major = DEFAULT_JAVA_MAJOR
        javaName = DEFAULT_JAVA_NAME
        if (
            self.javaVersion is not None
        ):  # some versions don't have this. TODO: maybe maintain manual overrides
            major = self.javaVersion.major_version
            javaName = self.javaVersion.component

        compatible_java_majors = [major]
        if (
            major in COMPATIBLE_JAVA_MAPPINGS
        ):  # add more compatible Java versions, e.g. 16 and 17 both work for MC 1.17
            compatible_java_majors += COMPATIBLE_JAVA_MAPPINGS[major]

        if new_type == "pending":  # experiments from upstream are type=pending
            new_type = "experiment"

        meta_version = MetaVersion(
            name=name,
            uid=uid,
            version=version,
            asset_index=self.asset_index,
            libraries=self.libraries,
            main_class=self.main_class,
            minecraft_arguments=self.minecraft_arguments,
            release_time=self.release_time,
            type=new_type,
            compatible_java_majors=compatible_java_majors,
            compatible_java_name=javaName,
            additional_traits=addn_traits,
            main_jar=main_jar,
            logging=(self.logging or {}).get("client")
        )
        return apply_mojang_version_fixup(meta_version)


def apply_mojang_version_fixup(meta_version: MetaVersion) -> MetaVersion:
    """
    Applies manual fixups for known-broken Mojang metadata for 3D Shareware v1.34.
    """
    fix = MOJANG_VERSION_APRIL_2019_NON_STANDARD_FIX
    if getattr(meta_version, 'version', None) == "3D Shareware v1.34":
        meta_version.additional_traits = fix.get("+traits", meta_version.additional_traits)
        meta_version.asset_index = fix.get("assetIndex", meta_version.asset_index)
        meta_version.compatible_java_majors = fix.get("compatibleJavaMajors", meta_version.compatible_java_majors)
        meta_version.compatible_java_name = fix.get("compatibleJavaName", meta_version.compatible_java_name)
        meta_version.libraries = fix.get("libraries", meta_version.libraries)
        meta_version.logging = fix.get("logging", meta_version.logging)
        meta_version.main_class = fix.get("mainClass", meta_version.main_class)
        meta_version.main_jar = fix.get("mainJar", meta_version.main_jar)
        meta_version.minecraft_arguments = fix.get("minecraftArguments", meta_version.minecraft_arguments)
        meta_version.release_time = fix.get("releaseTime", meta_version.release_time)
        meta_version.type = fix.get("type", meta_version.type)
        meta_version.uid = fix.get("uid", meta_version.uid)
        meta_version.name = fix.get("name", meta_version.name)
        meta_version.version = fix.get("version", meta_version.version)
    return meta_version
