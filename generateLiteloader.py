import os
from datetime import datetime
from typing import List, Tuple, Dict, Optional

from meta.common import ensure_component_dir, launcher_path, upstream_path
from meta.common.liteloader import LITELOADER_COMPONENT, VERSIONS_FILE
from meta.common.mojang import MINECRAFT_COMPONENT
from meta.model import MetaVersion, GradleSpecifier, Library, MetaPackage, Dependency
from meta.model.liteloader import LiteloaderIndex, LiteloaderArtefact

LAUNCHER_DIR = launcher_path()
UPSTREAM_DIR = upstream_path()

ensure_component_dir(LITELOADER_COMPONENT)


def process_artefacts(mc_version: str, artefacts: Dict[str, LiteloaderArtefact], is_snapshot: bool) \
        -> Tuple[List[MetaVersion], Optional[MetaVersion]]:
    versions: List[MetaVersion] = []
    lookup: Dict[str, MetaVersion] = {}
    latest_version = None
    latest = None
    for x, artefact in artefacts.items():
        if x == 'latest':
            latest_version = artefact.version
            continue
        v = MetaVersion(
            name="LiteLoader",
            uid=LITELOADER_COMPONENT,
            version=artefact.version,
            requires=[Dependency(uid=MINECRAFT_COMPONENT, equals=mc_version)],
            release_time=datetime.utcfromtimestamp(int(artefact.timestamp)),
            additional_tweakers=[artefact.tweakClass],
            main_class="net.minecraft.launchwrapper.Launch",
            order=10,
            libraries=artefact.libraries,
            type="release")

        if is_snapshot:
            v.type = "snapshot"

        # hack to make broken liteloader versions work
        for lib in v.libraries:
            if lib.name == GradleSpecifier("org.ow2.asm", "asm-all", "5.0.3"):
                lib.url = "https://repo.maven.apache.org/maven2/"
            if lib.name == GradleSpecifier("org.ow2.asm", "asm-all", "5.2"):
                lib.url = "http://repo.liteloader.com/"

        liteloader_lib = Library(
            name=GradleSpecifier("com.mumfrey", "liteloader", v.version),
            url="http://dl.liteloader.com/versions/"
        )
        if is_snapshot:
            liteloader_lib.mmcHint = "always-stale"
        v.libraries.append(liteloader_lib)

        versions.append(v)
        lookup[v.version] = v

    if latest_version:
        latest = lookup[latest_version]
    return versions, latest


def process_versions(index: LiteloaderIndex) -> Tuple[List[MetaVersion], List[str]]:
    all_versions: List[MetaVersion] = []
    recommended: List[str] = []
    for mcVersion, versionObject in index.versions.items():
        # ignore this for now. It should be a jar mod or something.
        if mcVersion == "1.5.2":
            continue

        latest_release = None
        if versionObject.artefacts:
            versions, latest_release = process_artefacts(mcVersion, versionObject.artefacts.liteloader, False)
            all_versions.extend(versions)
        if versionObject.snapshots:
            versions, latest_snapshot = process_artefacts(mcVersion, versionObject.snapshots.liteloader, True)
            all_versions.extend(versions)

        if latest_release:
            recommended.append(latest_release.version)

    recommended.sort()

    all_versions.sort(key=lambda x: x.release_time, reverse=True)
    return all_versions, recommended


def main():
    index = LiteloaderIndex.parse_file(os.path.join(UPSTREAM_DIR, VERSIONS_FILE))

    all_versions, recommended = process_versions(index)

    for version in all_versions:
        version.write(os.path.join(LAUNCHER_DIR, LITELOADER_COMPONENT, f"{version.version}.json"))

    package = MetaPackage(uid=LITELOADER_COMPONENT,
                          name='LiteLoader',
                          description=index.meta.description,
                          project_url=index.meta.url,
                          authors=[index.meta.authors],
                          recommended=recommended)
    package.write(os.path.join(LAUNCHER_DIR, LITELOADER_COMPONENT, "package.json"))


if __name__ == '__main__':
    main()
