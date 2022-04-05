from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import validator, Field

from . import MetaBase, MojangArtifactBase, MojangAssets, MojangLibrary, MojangArtifact, MojangLibraryDownloads, \
    Library, MetaVersion, GradleSpecifier

SUPPORTED_LAUNCHER_VERSION = 21
SUPPORTED_COMPLIANCE_LEVEL = 1

'''
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
'''


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
        self.versions: Dict[str, ExperimentEntry] = dict((x.id, x) for x in index.experiments)


class LegacyOverrideEntry(MetaBase):
    main_class: Optional[str] = Field(alias="mainClass")
    applet_class: Optional[str] = Field(alias="appletClass")
    release_time: Optional[datetime] = Field(alias="releaseTime")
    additional_traits: Optional[List[str]] = Field(alias="+traits")

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
            meta_version.additional_traits = meta_version.additional_traits + self.additional_traits

        if legacy:
            # remove all libraries - they are not needed for legacy
            meta_version.libraries = None
            # remove minecraft arguments - we use our own hardcoded ones
            meta_version.minecraft_arguments = None


class LegacyOverrideIndex(MetaBase):
    versions: Dict[str, LegacyOverrideEntry]


class MojangArguments(MetaBase):
    game: Optional[List[Any]]  # mixture of strings and objects
    jvm: Optional[List[Any]]


class MojangLoggingArtifact(MojangArtifactBase):
    id: str


class MojangLogging(MetaBase):
    @validator("type")
    def validate_type(cls, v):
        assert v in ["log4j2-xml"]
        return v

    file: MojangLoggingArtifact
    argument: str
    type: str


class JavaVersion(MetaBase):
    component: str = "jre-legacy"
    major_version: int = Field(8, alias="majorVersion")


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
    libraries: Optional[List[MojangLibrary]]  # TODO: optional?
    main_class: Optional[str] = Field(alias="mainClass")
    applet_class: Optional[str] = Field(alias="appletClass")
    processArguments: Optional[str]
    minecraft_arguments: Optional[str] = Field(alias="minecraftArguments")
    minimum_launcher_version: Optional[int] = Field(
        alias="minimumLauncherVersion")  # TODO: validate validateSupportedMojangVersion
    release_time: Optional[datetime] = Field(alias="releaseTime")
    time: Optional[datetime]
    type: Optional[str]
    inheritsFrom: Optional[str]
    logging: Optional[Dict[str, MojangLogging]]  # TODO improve this?
    compliance_level: Optional[int] = Field(alias="complianceLevel")
    javaVersion: Optional[JavaVersion]

    def to_meta_version(self, name: str, uid: str, version: str) -> MetaVersion:
        main_jar = None
        addn_traits = None
        new_type = self.type
        compatible_java_majors = None
        if self.id:
            client_download = self.downloads['client']
            artifact = MojangArtifact(url=client_download.url, sha1=client_download.sha1, size=client_download.size)
            downloads = MojangLibraryDownloads(artifact=artifact)
            main_jar = Library(name=GradleSpecifier("com.mojang", "minecraft", self.id, "client"), downloads=downloads)

        if not self.compliance_level:  # both == 0 and is None
            pass
        elif self.compliance_level == 1:
            if not addn_traits:
                addn_traits = []
            addn_traits.append("XR:Initial")
        else:
            raise Exception(f"Unsupported compliance level {self.compliance_level}")

        if self.javaVersion is not None:  # some versions don't have this. TODO: maybe maintain manual overrides
            major = self.javaVersion.major_version
            compatible_java_majors = [major]
            if major == 16:  # TODO: deal with this somewhere else
                compatible_java_majors.append(17)

        if new_type == "pending":  # TODO: why wasn't this needed before large refactor
            new_type = "experiment"

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
            additional_traits=addn_traits,
            main_jar=main_jar)
