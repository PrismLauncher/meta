import os.path
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

        return super(MetaBase, self).json(exclude_none=True, sort_keys=True, indent=4, **kwargs)

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
        return v > META_FORMAT_VERSION

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
    classifiers: Dict[Any, MojangArtifact]


class OSRule(MetaBase):
    @validator("name")
    def name_must_be_os(cls, v):
        return v in ["osx", "linux", "windows"]

    name: str
    version: Optional[str]


class MojangRule(MetaBase):
    @validator("action")
    def action_must_be_allow_disallow(cls, v):
        return v in ["allow", "disallow"]

    action: str
    os: Optional[OSRule]


class MojangLibrary(MetaBase):
    extract: Optional[MojangLibraryExtractRules]
    name: GradleSpecifier
    downloads: Optional[MojangLibraryDownloads]
    natives: Optional[Dict[str, str]]
    rules: Optional[List[MojangRule]]

    class Config:
        arbitrary_types_allowed = True


class Dependency(MetaBase):
    uid: str
    equals: Optional[str]
    suggests: Optional[str]


class Library(MojangLibrary):
    url: Optional[str]
    mmcHint: Optional[AnyHttpUrl] = Field(None, alias="MMC-hint")


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
    additional_traits: Optional[List[str]] = Field(alias="+traits")
    additional_tweakers: Optional[List[str]] = Field(alias="+tweakers")


class MetaPackageData(Versioned):
    name: str
    uid: str
    recommended: Optional[List[str]]
    authors: Optional[List[str]]
    description: Optional[str]
    project_url: Optional[AnyHttpUrl] = Field(alias="projectUrl")
