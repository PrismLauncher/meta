from datetime import datetime
from typing import Optional, List, Union

from pydantic import Field

from . import Library, MetaBase


class FabricInstallerArguments(MetaBase):
    client: Optional[List[str]] = None
    common: Optional[List[str]] = None
    server: Optional[List[str]] = None


class FabricInstallerLaunchwrapper(MetaBase):
    tweakers: FabricInstallerArguments


class FabricInstallerLibraries(MetaBase):
    client: Optional[List[Library]] = None
    common: Optional[List[Library]] = None
    server: Optional[List[Library]] = None


class FabricMainClasses(MetaBase):
    client: Optional[str] = None
    common: Optional[str] = None
    server: Optional[str] = None


class FabricInstallerDataV1(MetaBase):
    version: int
    libraries: FabricInstallerLibraries
    main_class: Optional[Union[str, FabricMainClasses]] = Field(None, alias="mainClass")
    arguments: Optional[FabricInstallerArguments] = None
    launchwrapper: Optional[FabricInstallerLaunchwrapper] = None


class FabricJarInfo(MetaBase):
    release_time: Optional[datetime] = Field(None, alias="releaseTime")
