from datetime import datetime
from typing import Optional, List, Union

from pydantic import Field

from . import Library, MetaBase


class FabricInstallerArguments(MetaBase):
    client: Optional[List[str]]
    common: Optional[List[str]]
    server: Optional[List[str]]


class FabricInstallerLaunchwrapper(MetaBase):
    tweakers: FabricInstallerArguments


class FabricInstallerLibraries(MetaBase):
    client: Optional[List[Library]]
    common: Optional[List[Library]]
    server: Optional[List[Library]]


class FabricMainClasses(MetaBase):
    client: Optional[str]
    common: Optional[str]
    server: Optional[str]


class FabricInstallerDataV1(MetaBase):
    version: int
    libraries: FabricInstallerLibraries
    main_class: Optional[Union[str, FabricMainClasses]] = Field(alias="mainClass")
    arguments: Optional[FabricInstallerArguments]
    launchwrapper: Optional[FabricInstallerLaunchwrapper]


class FabricJarInfo(MetaBase):
    release_time: Optional[datetime] = Field(alias="releaseTime")
