from datetime import datetime
from typing import Optional, List

from . import MetaBase

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
    releaseTime: Optional[datetime]
    time: Optional[datetime]
    type: Optional[str]
    url: Optional[str]
    sha1: Optional[str]
    complianceLevel: Optional[int]


class MojangIndex(MetaBase):
    latest: MojangLatestVersion
    versions: List[MojangIndexEntry]


class MojangIndexWrap:
    def __init__(self, index: MojangIndex):
        self.index = index
        self.latest = index.latest
        self.versions = dict((x.id, x) for x in index.versions)
