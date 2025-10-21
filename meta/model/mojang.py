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
        else:
            new_type = new_type.removeprefix("old_")

        return MetaVersion(
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
