import json
import os
from datetime import datetime, timezone

from meta.common import ensure_component_dir, launcher_path, upstream_path
from meta.common.cleanroom import BASE_DIR, VERSIONS_FILE, COMPONENT, MINECRAFT_VERSION
from meta.model import (
    Dependency,
    GradleSpecifier,
    Library,
    MetaPackage,
    MetaVersion,
    MojangArtifact,
    MojangLibraryDownloads,
)

CONFLICTS = [
    "net.minecraftforge",
    "net.neoforged",
    "net.fabricmc.fabric-loader",
    "org.quiltmc.quilt-loader",
    "org.lwjgl",
]


def parse_library(raw: dict) -> Library:
    name = GradleSpecifier.from_string(raw["name"])
    downloads = None
    if "downloads" in raw:
        artifact = None
        if "artifact" in raw["downloads"]:
            a = raw["downloads"]["artifact"]
            artifact = MojangArtifact(
                url=a["url"],
                sha1=a.get("sha1"),
                size=a.get("size"),
                path=a.get("path"),
            )
        downloads = MojangLibraryDownloads(artifact=artifact)
    url = raw.get("url")
    return Library(name=name, downloads=downloads, url=url)


def parse_release_time(raw: dict) -> datetime:
    ts = raw.get("releaseTime", "1970-01-01T00:00:00+00:00")
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def process_version(tag: str, patch: dict, lwjgl3_version: str | None) -> MetaVersion:
    version = patch.get("version", tag)

    v = MetaVersion(
        name="Cleanroom",
        uid=COMPONENT,
        version=version,
        release_time=parse_release_time(patch),
        requires=[
            Dependency(uid="net.minecraft", equals=MINECRAFT_VERSION),
            Dependency(uid="org.lwjgl3", suggests=lwjgl3_version),
        ],
        conflicts=[Dependency(uid=uid) for uid in CONFLICTS],
        satisfies=[Dependency(uid="org.lwjgl")],
        main_class=patch.get("mainClass"),
        additional_tweakers=patch.get("+tweakers"),
        additional_jvm_args=patch.get("+jvmArgs"),
        libraries=[parse_library(lib) for lib in patch.get("libraries", [])],
        order=10,
        type="alpha",
    )
    return v


def main():
    launcher_dir = launcher_path()
    upstream_dir = upstream_path()

    ensure_component_dir(COMPONENT)
    ensure_component_dir("net.minecraft")
    ensure_component_dir("org.lwjgl3")

    index_path = os.path.join(upstream_dir, VERSIONS_FILE)
    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    recommended: str | None = None
    lwjgl3_versions: dict[str, dict] = {}
    recommended_minecraft_patch: dict | None = None

    for entry in index:
        tag = entry["version"]
        patch_path = os.path.join(upstream_dir, BASE_DIR, f"{tag}.json")
        if not os.path.exists(patch_path):
            print(f"Missing upstream for {tag}, skipping")
            continue

        with open(patch_path, "r", encoding="utf-8") as f:
            patch = json.load(f)

        lwjgl3_version = None

        lwjgl3_patch_path = os.path.join(upstream_dir, BASE_DIR, f"{tag}-lwjgl3.json")
        if os.path.exists(lwjgl3_patch_path):
            with open(lwjgl3_patch_path, "r", encoding="utf-8") as f:
                lwjgl3_patch = json.load(f)
            lwjgl3_version = lwjgl3_patch.get("version")
            if lwjgl3_version and lwjgl3_version not in lwjgl3_versions:
                lwjgl3_versions[lwjgl3_version] = lwjgl3_patch

        minecraft_patch_path = os.path.join(
            upstream_dir, BASE_DIR, f"{tag}-minecraft.json"
        )
        minecraft_patch = None
        if os.path.exists(minecraft_patch_path):
            with open(minecraft_patch_path, "r", encoding="utf-8") as f:
                minecraft_patch = json.load(f)

        java_majors = (
            minecraft_patch.get("compatibleJavaMajors", []) if minecraft_patch else []
        )
        print(
            f"Processing Cleanroom {tag} (mc={MINECRAFT_VERSION}, lwjgl3={lwjgl3_version}, java={java_majors})"
        )
        v = process_version(tag, patch, lwjgl3_version)

        if recommended is None:
            recommended = v.version
            recommended_minecraft_patch = minecraft_patch

        v.write(os.path.join(launcher_dir, COMPONENT, f"{v.version}.json"))

    if recommended_minecraft_patch:
        dest = os.path.join(launcher_dir, "net.minecraft", f"{MINECRAFT_VERSION}.json")
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(recommended_minecraft_patch, f, sort_keys=True, indent=4)
        MetaPackage(
            uid="net.minecraft", name="Minecraft", recommended=[MINECRAFT_VERSION]
        ).write(os.path.join(launcher_dir, "net.minecraft", "package.json"))
        print(f"Wrote patched net.minecraft {MINECRAFT_VERSION}")

    for lwjgl3_version, lwjgl3_patch in lwjgl3_versions.items():
        dest = os.path.join(launcher_dir, "org.lwjgl3", f"{lwjgl3_version}.json")
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(lwjgl3_patch, f, sort_keys=True, indent=4)
        print(f"Wrote org.lwjgl3 {lwjgl3_version}")
    if lwjgl3_versions:

        def lwjgl3_version_key(v: str) -> tuple[int, ...]:
            return tuple(int(x) for x in v.split("-")[0].split("."))

        lwjgl3_recommended = sorted(
            lwjgl3_versions.keys(), key=lwjgl3_version_key, reverse=True
        )
        MetaPackage(
            uid="org.lwjgl3", name="LWJGL 3", recommended=[lwjgl3_recommended[0]]
        ).write(os.path.join(launcher_dir, "org.lwjgl3", "package.json"))

    package = MetaPackage(
        uid=COMPONENT,
        name="Cleanroom",
        recommended=[recommended] if recommended else [],
        description=(
            "Cleanroom is a Forge-compatible mod loader for Minecraft 1.12.2 "
            "with support for modern Java (Java 25+)."
        ),
        project_url="https://github.com/CleanroomMC/Cleanroom",
        authors=["CleanroomMC"],
    )
    package.write(os.path.join(launcher_dir, COMPONENT, "package.json"))
    print(f"Done. Recommended: {recommended or 'none'}")


if __name__ == "__main__":
    main()
