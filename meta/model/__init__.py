import copy
from datetime import datetime
from typing import Optional, List, Dict, Any, Iterator

import pydantic
from pydantic import Field, validator

from ..common import serialize_datetime, replace_old_launchermeta_url, get_all_bases, merge_dict

META_FORMAT_VERSION = 1


class GradleSpecifier:
    """
        A gradle specifier - a maven coordinate. Like one of these:
        "org.lwjgl.lwjgl:lwjgl:2.9.0"
        "net.java.jinput:jinput:2.0.5"
        "net.minecraft:launchwrapper:1.5"
    """

    def __init__(self, group: str, artifact: str, version: str, classifier: Optional[str] = None,
                 extension: Optional[str] = None):
        if extension is None:
            extension = "jar"
        self.group = group
        self.artifact = artifact
        self.version = version
        self.classifier = classifier
        self.extension = extension

    def __str__(self):
        ext = ''
        if self.extension != 'jar':
            ext = "@%s" % self.extension
        if self.classifier:
            return "%s:%s:%s:%s%s" % (self.group, self.artifact, self.version, self.classifier, ext)
        else:
            return "%s:%s:%s%s" % (self.group, self.artifact, self.version, ext)

    def filename(self):
        if self.classifier:
            return "%s-%s-%s.%s" % (self.artifact, self.version, self.classifier, self.extension)
        else:
            return "%s-%s.%s" % (self.artifact, self.version, self.extension)

    def base(self):
        return "%s/%s/%s/" % (self.group.replace('.', '/'), self.artifact, self.version)

    def path(self):
        return self.base() + self.filename()

    def __repr__(self):
        return f"GradleSpecifier('{self}')"

    def is_lwjgl(self):
        return self.group in ("org.lwjgl", "org.lwjgl.lwjgl", "net.java.jinput", "net.java.jutils")

    def is_log4j(self):
        return self.group == "org.apache.logging.log4j"

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other):
        return str(self) < str(other)

    def __gt__(self, other):
        return str(self) > str(other)

    def __hash__(self):
        return hash(str(self))

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def from_string(cls, v: str):
        ext_split = v.split('@')

        components = ext_split[0].split(':')
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
    def validate(cls, v):
        if isinstance(v, cls):
            return v
        if isinstance(v, str):
            return cls.from_string(v)
        raise TypeError("Invalid type")


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

    def merge(self, other):
        """
        Merge other object with self.
        - Concatenates lists
        - Combines sets
        - Merges dictionaries (other takes priority)
        - Recurses for all fields that are also MetaBase classes
        - Overwrites for any other field type (int, string, ...)
        """
        assert type(other) is type(self)
        for key, field in self.__fields__.items():
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
                result = merge_dict(ours, copy.deepcopy(theirs))
                setattr(self, key, result)
            elif MetaBase in get_all_bases(field.type_):
                ours.merge(theirs)
            else:
                setattr(self, key, theirs)

    def __hash__(self):
        return hash(self.json())

    class Config:
        allow_population_by_field_name = True

        json_encoders = {
            datetime: serialize_datetime,
            GradleSpecifier: str
        }


class Versioned(MetaBase):
    @validator("format_version")
    def format_version_must_be_supported(cls, v):
        assert v <= META_FORMAT_VERSION
        return v

    format_version: int = Field(META_FORMAT_VERSION, alias="formatVersion")


class MojangArtifactBase(MetaBase):
    sha1: Optional[str]
    size: Optional[int]
    url: str


class MojangAssets(MojangArtifactBase):
    @validator("url")
    def validate_url(cls, v):
        return replace_old_launchermeta_url(v)

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
        assert v in ["osx", "linux", "windows", "windows-arm64", "osx-arm64", "linux-arm64", "linux-arm32"]
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

    def __iter__(self) -> Iterator[MojangRule]:
        return iter(self.__root__)

    def __getitem__(self, item) -> MojangRule:
        return self.__root__[item]


class MojangLibrary(MetaBase):
    extract: Optional[MojangLibraryExtractRules]
    name: Optional[GradleSpecifier]
    downloads: Optional[MojangLibraryDownloads]
    natives: Optional[Dict[str, str]]
    rules: Optional[MojangRules]


class Library(MojangLibrary):
    url: Optional[str]
    mmcHint: Optional[str] = Field(None, alias="MMC-hint")


class Dependency(MetaBase):
    uid: str
    equals: Optional[str]
    suggests: Optional[str]


class MetaVersion(Versioned):
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


class MetaPackage(Versioned):
    name: str
    uid: str
    recommended: Optional[List[str]]
    authors: Optional[List[str]]
    description: Optional[str]
    project_url: Optional[str] = Field(alias="projectUrl")
