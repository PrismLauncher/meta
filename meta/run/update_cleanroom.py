import io
import json
import os
import zipfile

from meta.common import upstream_path, ensure_upstream_dir, default_session
from meta.common.cleanroom import BASE_DIR, VERSIONS_FILE, GITHUB_REPO
from meta.common.http import get_github_releases

UPSTREAM_DIR = upstream_path()

ensure_upstream_dir(BASE_DIR)

sess = default_session()


PATCHES = {
    "net.minecraftforge.json": "{tag}.json",
    "net.minecraft.json": "{tag}-minecraft.json",
    "org.lwjgl3.json": "{tag}-lwjgl3.json",
}


def get_mmc_patches(tag: str) -> dict[str, dict]:
    zip_url = (
        f"https://github.com/{GITHUB_REPO}/releases/download/"
        f"{tag}/Cleanroom-MMC-instance-{tag}.zip"
    )
    r = sess.get(zip_url)
    r.raise_for_status()
    result = {}
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        for patch_name in PATCHES:
            with zf.open(f"patches/{patch_name}") as f:
                result[patch_name] = json.load(f)
    return result


def main():
    releases = get_github_releases(sess, GITHUB_REPO)

    versions = []
    for release in releases:
        tag = release["tag_name"]
        published_at = release["published_at"]

        dest_paths = [
            os.path.join(UPSTREAM_DIR, BASE_DIR, dest_template.format(tag=tag))
            for dest_template in PATCHES.values()
        ]
        if all(os.path.exists(p) for p in dest_paths):
            print(f"Already have Cleanroom {tag}")
            versions.append({"version": tag, "published_at": published_at})
            continue

        print(f"Downloading Cleanroom {tag}")
        try:
            patches = get_mmc_patches(tag)
        except Exception as e:
            print(f"  Skipping {tag}: {e}")
            continue

        for patch_name, dest_template in PATCHES.items():
            patch = patches[patch_name]
            patch.setdefault("releaseTime", published_at)
            dest = os.path.join(UPSTREAM_DIR, BASE_DIR, dest_template.format(tag=tag))
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(patch, f, sort_keys=True, indent=4)

        versions.append({"version": tag, "published_at": published_at})

    index_path = os.path.join(UPSTREAM_DIR, VERSIONS_FILE)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(versions, f, sort_keys=True, indent=4)
    print(f"Wrote index with {len(versions)} versions")


if __name__ == "__main__":
    main()
