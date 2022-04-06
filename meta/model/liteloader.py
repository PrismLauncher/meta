from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import Field

from . import Library, MetaBase


class LiteloaderDev(MetaBase):
    fgVersion: Optional[str]
    mappings: Optional[str]
    mcp: Optional[str]


class LiteloaderRepo(MetaBase):
    """
        "repo":{
            "stream":"RELEASE",
            "type":"m2",
            "url":"http://dl.liteloader.com/repo/",
            "classifier":""
        },
    """
    stream: str
    type: str
    url: str
    classifier: str


class LiteloaderArtefact(MetaBase):
    """
        "53639d52340479ccf206a04f5e16606f":{
            "tweakClass":"com.mumfrey.liteloader.launch.LiteLoaderTweaker",
            "libraries":[
                {
                    "name":"net.minecraft:launchwrapper:1.5"
                },
                {
                    "name":"net.sf.jopt-simple:jopt-simple:4.5"
                },
                {
                    "name":"org.ow2.asm:asm-all:4.1"
                }
            ],
            "stream":"RELEASE",
            "file":"liteloader-1.5.2_01.jar",
            "version":"1.5.2_01",
            "md5":"53639d52340479ccf206a04f5e16606f",
            "timestamp":"1367366420"
        },
    """
    tweakClass: str
    libraries: List[Library]
    stream: str
    file: str
    version: str
    build: Optional[str]
    md5: str
    timestamp: str
    srcJar: Optional[str]
    mcpJar: Optional[str]
    lastSuccessfulBuild: Optional[int]  # only for snapshots


class LiteloaderArtefacts(MetaBase):
    liteloader: Dict[str, LiteloaderArtefact] = Field(alias="com.mumfrey:liteloader")
    libraries: Optional[List[Library]]


class LiteloaderEntry(MetaBase):
    """
        "1.10.2":{
            "dev": { ... },
            "repo":{ ... },
            "artefacts":{
                "com.mumfrey:liteloader":{ },
                ...
            },
            "snapshots":{
                ...
            }
    """
    dev: Optional[LiteloaderDev]
    repo: LiteloaderRepo
    artefacts: Optional[LiteloaderArtefacts]
    snapshots: Optional[LiteloaderArtefacts]


class LiteloaderMeta(MetaBase):
    """
        "meta":{
            "description":"LiteLoader is a lightweight mod bootstrap designed to provide basic loader functionality for mods which don't need to modify game mechanics.",
            "authors":"Mumfrey",
            "url":"http://dl.liteloader.com",
            "updated":"2017-02-22T11:34:07+00:00",
            "updatedTime":1487763247
        },
    """
    description: str
    authors: str
    url: str
    updated: datetime
    updated_time: int = Field(alias="updatedTime")


class LiteloaderIndex(MetaBase):
    meta: LiteloaderMeta
    versions: Dict[Any, LiteloaderEntry]
