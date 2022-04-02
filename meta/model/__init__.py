from datetime import datetime
from typing import Optional, List, Dict, Any

import pydantic
from pydantic import Field, AnyHttpUrl, validator

from .types import GradleSpecifier
from ..common import serialize_datetime

META_FORMAT_VERSION = 1


class MetaBase(pydantic.BaseModel):
    def dict(self, **kwargs) -> Dict[str, Any]:
        for k in ["by_alias"]:
            if k in kwargs:
                del kwargs[k]

        return super(MetaBase, self).dict(by_alias=True, **kwargs)

    def json(self, **kwargs: Any) -> str:
        for k in ["exclude_none", "sort_keys", "indent"]:
            if k in kwargs:
                del kwargs[k]

        return super(MetaBase, self).json(exclude_none=True, sort_keys=True, by_alias=True, indent=4, **kwargs)

    def write(self, file_path):
        with open(file_path, "w") as f:
            f.write(self.json())

    class Config:
        allow_population_by_field_name = True

        json_encoders = {
            datetime: serialize_datetime
        }


class Versioned(MetaBase):
    @validator("format_version")
    def format_version_must_be_supported(cls, v):
        assert v > META_FORMAT_VERSION
        return v

    format_version: int = Field(META_FORMAT_VERSION, alias="formatVersion")


class MojangArtifactBase(MetaBase):
    sha1: Optional[str]
    size: Optional[int]
    url: AnyHttpUrl


class MojangAssets(MojangArtifactBase):
    id: str
    totalSize: int


class MojangArtifact(MojangArtifactBase):
    path: Optional[str]


class MojangLibraryExtractRules(MetaBase):
    """
            "rules": [
                {
                    "action": "allow"
                },
                {
                    "action": "disallow",
                    "os": {
                        "name": "osx"
                    }
                }
            ]
    """
    exclude: List[str]  # TODO maybe drop this completely?


class MojangLibraryDownloads(MetaBase):
    artifact: Optional[MojangArtifact]
    classifiers: Optional[Dict[Any, MojangArtifact]]


class OSRule(MetaBase):
    @validator("name")
    def name_must_be_os(cls, v):
        assert v in ["osx", "linux", "windows"]
        return v

    name: str
    version: Optional[str]


class MojangRule(MetaBase):
    @validator("action")
    def action_must_be_allow_disallow(cls, v):
        assert v in ["allow", "disallow"]
        return v

    action: str
    os: Optional[OSRule]


class MojangRules(MetaBase):
    __root__: List[MojangRule]

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]


class MojangLibrary(MetaBase):
    @validator("name")
    def validate_name(cls, v):
        if v is not GradleSpecifier:
            return GradleSpecifier(v)
        return v

    extract: Optional[MojangLibraryExtractRules]
    name: GradleSpecifier
    downloads: Optional[MojangLibraryDownloads]
    natives: Optional[Dict[str, str]]
    rules: Optional[MojangRules]


class Library(MojangLibrary):
    url: Optional[str]
    mmcHint: Optional[AnyHttpUrl] = Field(None, alias="MMC-hint")


class Dependency(MetaBase):
    uid: str
    equals: Optional[str]
    suggests: Optional[str]


class MetaVersionFile(Versioned):
    name: str
    version: str
    uid: str
    type: Optional[str]
    order: Optional[int]
    volatile: Optional[bool]
    requires: Optional[List[Dependency]]
    conflicts: Optional[List[Dependency]]
    libraries: Optional[List[Library]]
    asset_index: Optional[MojangAssets] = Field(alias="assetIndex")
    maven_files: Optional[List[Library]] = Field(alias="mavenFiles")
    main_jar: Optional[Library] = Field(alias="mainJar")
    jar_mods: Optional[List[Library]] = Field(alias="jarMods")
    main_class: Optional[str] = Field(alias="mainClass")
    applet_class: Optional[str] = Field(alias="appletClass")
    minecraft_arguments: Optional[str] = Field(alias="minecraftArguments")
    release_time: Optional[datetime] = Field(alias="releaseTime")
    compatible_java_majors: Optional[List[int]] = Field(alias="compatibleJavaMajors")
    additional_traits: Optional[List[str]] = Field(alias="+traits")
    additional_tweakers: Optional[List[str]] = Field(alias="+tweakers")


class MetaPackageData(Versioned):
    name: str
    uid: str
    recommended: Optional[List[str]]
    authors: Optional[List[str]]
    description: Optional[str]
    project_url: Optional[AnyHttpUrl] = Field(alias="projectUrl")
