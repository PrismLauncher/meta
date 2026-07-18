from datetime import datetime
from typing import Optional, List

from pydantic import Field

from meta.model import Dependency, MetaBase, Versioned, MetaVersion


class MetaVersionIndexEntry(MetaBase):
    version: str
    type: Optional[str] = None
    release_time: datetime = Field(alias="releaseTime")
    requires: Optional[List[Dependency]] = None
    conflicts: Optional[List[Dependency]] = None
    recommended: Optional[bool] = None
    volatile: Optional[bool] = None
    sha256: str

    @classmethod
    def from_meta_version(cls, v: MetaVersion, recommended: bool, sha256: str):
        return cls(
            version=v.version,
            type=v.type,
            release_time=v.release_time,
            requires=v.requires,
            conflicts=v.conflicts,
            recommended=recommended,
            volatile=v.volatile,
            sha256=sha256,
        )


class MetaVersionIndex(Versioned):
    name: str
    uid: str
    versions: List[MetaVersionIndexEntry] = Field([])


class MetaPackageIndexEntry(MetaBase):
    name: str
    uid: str
    sha256: str


class MetaPackageIndex(Versioned):
    packages: List[MetaPackageIndexEntry] = Field([])
