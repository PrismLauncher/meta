import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

import pydantic
from pydantic import (
    field_validator,
    field_serializer,
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
)
from pydantic.json_schema import GetJsonSchemaHandler
from pydantic_core import core_schema

from ..common import (
    LAUNCHER_MAVEN,
    replace_old_launchermeta_url,
    get_all_bases,
    merge_dict,
)

META_FORMAT_VERSION = 1


class GradleSpecifier:
    """
    A gradle specifier - a maven coordinate. Like one of these:
    "org.lwjgl.lwjgl:lwjgl:2.9.0"
    "net.java.jinput:jinput:2.0.5"
    "net.minecraft:launchwrapper:1.5"
    """

    def __init__(
        self,
        group: str,
        artifact: str,
        version: str,
        classifier: Optional[str] = None,
        extension: Optional[str] = None,
    ):
        if extension is None:
            extension = "jar"
        self.group = group
        self.artifact = artifact
        self.version = version
        self.classifier = classifier
        self.extension = extension

    def __str__(self):
        ext = ""
        if self.extension != "jar":
            ext = "@%s" % self.extension
        if self.classifier:
            return "%s:%s:%s:%s%s" % (
                self.group,
                self.artifact,
                self.version,
                self.classifier,
                ext,
            )
        else:
            return "%s:%s:%s%s" % (self.group, self.artifact, self.version, ext)

    def filename(self):
        if self.classifier:
            return "%s-%s-%s.%s" % (
                self.artifact,
                self.version,
                self.classifier,
                self.extension,
            )
        else:
            return "%s-%s.%s" % (self.artifact, self.version, self.extension)

    def base(self):
        return "%s/%s/%s/" % (self.group.replace(".", "/"), self.artifact, self.version)

    def path(self):
        return self.base() + self.filename()

    def __repr__(self):
        return f"GradleSpecifier('{self}')"

    def is_lwjgl(self):
        return self.group in (
            "org.lwjgl",
            "org.lwjgl.lwjgl",
            "net.java.jinput",
            "net.java.jutils",
        )

    def is_log4j(self):
        return self.group == "org.apache.logging.log4j"

    def __eq__(self, other: Any):
        if isinstance(other, GradleSpecifier):
            return str(self) == str(other)
        else:
            return False

    def __lt__(self, other: "GradleSpecifier"):
        return str(self) < str(other)

    def __gt__(self, other: "GradleSpecifier"):
        return str(self) > str(other)

    def __hash__(self):
        return hash(str(self))

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls.validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: str(v), info_arg=False
            ),
        )

    @classmethod
    def from_string(cls, v: str):
        ext_split = v.split("@")

        components = ext_split[0].split(":")
        group = components[0]
        artifact = components[1]
        version = components[2]

        extension = None
        if len(ext_split) == 2:
            extension = ext_split[1]

        classifier = None
        if len(components) == 4:
            classifier = components[3]
        return cls(group, artifact, version, classifier, extension)

    @classmethod
    def validate(cls, v: "str | GradleSpecifier"):
        if isinstance(v, cls):
            return v
        if isinstance(v, str):
            return cls.from_string(v)
        raise TypeError("Invalid type")


class MetaBase(pydantic.BaseModel):
    @field_validator("*", mode="after")
    @classmethod
    def _ensure_utc(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @field_serializer("*", mode="wrap")
    @classmethod
    def _serialize_datetime(cls, v, handler, info):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            return v.isoformat()
        return handler(v)

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        for k in ["by_alias"]:
            if k in kwargs:
                del kwargs[k]

        return self.model_dump(by_alias=True, **kwargs)

    def json(self, **kwargs: Any) -> str:
        for k in ["exclude_none", "sort_keys", "indent"]:
            if k in kwargs:
                del kwargs[k]

        return json.dumps(
            self.model_dump(exclude_none=True, by_alias=True, mode="json"),
            sort_keys=True,
            indent=4,
        )

    def write(self, file_path: str):
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(self.json())

    def merge(self, other: "MetaBase"):
        """
        Merge other object with self.
        - Concatenates lists
        - Combines sets
        - Merges dictionaries (other takes priority)
        - Recurses for all fields that are also MetaBase classes
        - Overwrites for any other field type (int, string, ...)
        """
        assert type(other) is type(self)
        for key, field in type(self).model_fields.items():
            ours = getattr(self, key)
            theirs = getattr(other, key)
            if theirs is None:
                continue
            if ours is None:
                setattr(self, key, theirs)
                continue

            if isinstance(ours, list):
                ours += theirs
            elif isinstance(ours, set):
                ours |= theirs
            elif isinstance(ours, dict):
                result = merge_dict(ours, copy.deepcopy(theirs))  # type: ignore
                setattr(self, key, result)
            elif MetaBase in get_all_bases(field.annotation):
                ours.merge(theirs)
            else:
                setattr(self, key, theirs)

    def __hash__(self):  # type: ignore
        return hash(self.json())

    model_config = ConfigDict(
        populate_by_name=True,
    )


class Versioned(MetaBase):
    @field_validator("format_version")
    @classmethod
    def format_version_must_be_supported(cls, v: int):
        assert v <= META_FORMAT_VERSION
        return v

    format_version: int = Field(META_FORMAT_VERSION, alias="formatVersion")


class MojangArtifactBase(MetaBase):
    sha1: Optional[str] = None
    size: Optional[int] = None
    url: str


class MojangAssets(MojangArtifactBase):
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str):
        return replace_old_launchermeta_url(v)

    id: str
    totalSize: int


class MojangArtifact(MojangArtifactBase):
    path: Optional[str] = None


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
    artifact: Optional[MojangArtifact] = None
    classifiers: Optional[Dict[Any, MojangArtifact]] = None


class OSRule(MetaBase):
    @field_validator("name")
    @classmethod
    def name_must_be_os(cls, v: str):
        assert v in [
            "osx",
            "linux",
            "windows",
            "windows-arm64",
            "osx-arm64",
            "linux-arm64",
            "linux-arm32",
            "linux-riscv64",
        ]
        return v

    name: str
    version: Optional[str] = None


class MojangRule(MetaBase):
    @field_validator("action")
    @classmethod
    def action_must_be_allow_disallow(cls, v: str):
        assert v in ["allow", "disallow"]
        return v

    action: str
    os: Optional[OSRule] = None


class MojangLoggingArtifact(MojangArtifactBase):
    id: str


class MojangLogging(MetaBase):
    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        assert v in ["log4j2-xml"]
        return v

    file: MojangLoggingArtifact
    argument: str
    type: str


class Library(MetaBase):
    extract: Optional[MojangLibraryExtractRules] = None
    name: Optional[GradleSpecifier] = None
    downloads: Optional[MojangLibraryDownloads] = None
    natives: Optional[Dict[str, str]] = None
    rules: Optional[List[MojangRule]] = None
    url: Optional[str] = None
    mmcHint: Optional[str] = Field(None, alias="MMC-hint")


class JavaAgent(Library):
    argument: Optional[str] = None


class Dependency(MetaBase):
    uid: str
    equals: Optional[str] = None
    suggests: Optional[str] = None


class MetaVersion(Versioned):
    name: str
    version: str
    uid: str
    type: Optional[str] = None
    order: Optional[int] = None
    volatile: Optional[bool] = None
    requires: Optional[List[Dependency]] = None
    conflicts: Optional[List[Dependency]] = None
    libraries: Optional[List[Library]] = None
    asset_index: Optional[MojangAssets] = Field(None, alias="assetIndex")
    maven_files: Optional[List[Library]] = Field(None, alias="mavenFiles")
    main_jar: Optional[Library] = Field(None, alias="mainJar")
    jar_mods: Optional[List[Library]] = Field(None, alias="jarMods")
    main_class: Optional[str] = Field(None, alias="mainClass")
    applet_class: Optional[str] = Field(None, alias="appletClass")
    minecraft_arguments: Optional[str] = Field(None, alias="minecraftArguments")
    release_time: Optional[datetime] = Field(None, alias="releaseTime")
    compatible_java_majors: Optional[List[int]] = Field(
        None, alias="compatibleJavaMajors"
    )
    compatible_java_name: Optional[str] = Field(None, alias="compatibleJavaName")
    java_agents: Optional[List[JavaAgent]] = Field(None, alias="+agents")
    additional_traits: Optional[List[str]] = Field(None, alias="+traits")
    additional_tweakers: Optional[List[str]] = Field(None, alias="+tweakers")
    additional_jvm_args: Optional[List[str]] = Field(None, alias="+jvmArgs")
    logging: Optional[MojangLogging] = None


class MetaPackage(Versioned):
    name: str
    uid: str
    recommended: Optional[List[str]] = None
    authors: Optional[List[str]] = None
    description: Optional[str] = None
    project_url: Optional[str] = Field(None, alias="projectUrl")


def make_launcher_library(
    name: GradleSpecifier, hash: str, size: int, maven=LAUNCHER_MAVEN
):
    artifact = MojangArtifact(url=maven % name.path(), sha1=hash, size=size)
    return Library(name=name, downloads=MojangLibraryDownloads(artifact=artifact))
