import json
import os
import zipfile

from meta.common import upstream_path, ensure_upstream_dir, static_path, default_session
from meta.common.java import (
    BASE_DIR,
    ADOPTIUM_DIR,
    AZUL_DIR,
    ADOPTIUM_VERSIONS_DIR,
    AZUL_VERSIONS_DIR,
)
from meta.model.java import (
    ADOPTIUM_API_AVAILABLE_RELEASES,
    adoptiumAPIFeatureReleases,
    AdoptiumImageType,
    AdoptiumAPIFeatureReleasesQuery,
    AdoptiumAvailableReleases,
    AdoptiumRelease,
    AdoptiumReleasesWrap,
    azulApiPackages,
    AzulApiPackagesQuery,
    ZuluPackageList,
    ZuluPackagesListWrap,
    AzulArchiveType,
    AzulReleaseStatus,
    AzulAvailabilityType,
    AzulJavaPackageType,
    azulApiPackageDetail,
    ZuluPackageDetail,
    ZuluPackagesDetailListWrap,
)

UPSTREAM_DIR = upstream_path()
STATIC_DIR = static_path()

ensure_upstream_dir(BASE_DIR)
ensure_upstream_dir(ADOPTIUM_DIR)
ensure_upstream_dir(AZUL_DIR)
ensure_upstream_dir(ADOPTIUM_VERSIONS_DIR)
ensure_upstream_dir(AZUL_VERSIONS_DIR)


sess = default_session()


def main():
    print("Getting Adoptium Release Manifests ")
    r = sess.get(ADOPTIUM_API_AVAILABLE_RELEASES)
    r.raise_for_status()

    available = AdoptiumAvailableReleases(**r.json())

    available_releases_file = os.path.join(
        UPSTREAM_DIR, ADOPTIUM_DIR, "available_releases.json")
    available.write(available_releases_file)

    for feature in available.available_releases:
        print("Getting Manifests for Adoptium feature release:", feature)
        page = 0
        page_size = 10

        releases_for_feature: list[AdoptiumRelease] = []

        while True:
            query = AdoptiumAPIFeatureReleasesQuery(
                image_type=AdoptiumImageType.Jre, page_size=page_size, page=page)
            api_call = adoptiumAPIFeatureReleases(feature, query=query)
            print("Fetching Page:", page, api_call)
            r_rls = sess.get(api_call)
            if r_rls.status_code == 404:
                break
            else:
                r_rls.raise_for_status()

            releases = list(AdoptiumRelease(**rls) for rls in r_rls.json())
            releases_for_feature.extend(releases)

            if len(r_rls.json()) < page_size:
                break
            page += 1

        print("Total Adoptium releases for feature:", len(releases_for_feature))
        releases = AdoptiumReleasesWrap(releases=releases_for_feature)
        feature_file = os.path.join(
            UPSTREAM_DIR, ADOPTIUM_VERSIONS_DIR, "{}.json".format(feature))
        releases.write(feature_file)

    print("Getting Azul Release Manifests")
    zulu_packages: list[ZuluPackageList] = []
    page = 1
    page_size = 100
    while True:

        query = AzulApiPackagesQuery(
            archive_type=AzulArchiveType.Zip,
            release_status=AzulReleaseStatus.Ga,
            availability_types=[AzulAvailabilityType.CA],
            java_package_type=AzulJavaPackageType.Jre,
            javafx_bundled=False,
            page=page,
            page_size=page_size)
        api_call = azulApiPackages(query=query)

        print("Processing Page:", page, api_call)

        r = sess.get(api_call)
        if r.status_code == 404:
            break
        else:
            r.raise_for_status()

        packages = list(ZuluPackageList(**pkg) for pkg in r.json())
        zulu_packages.extend(packages)
        if len(packages) < page_size:
            break
        page += 1

    print("Total Azul Packages:", len(zulu_packages))
    packages = ZuluPackagesListWrap(packages=zulu_packages)
    azul_manifest_file = os.path.join(UPSTREAM_DIR, AZUL_DIR, "packages.json")
    packages.write(azul_manifest_file)

    azul_major_versions: dict[int, ZuluPackagesListWrap] = {}

    for pkg in packages.packages:

        major_version = pkg.java_version[0]
        if major_version not in azul_major_versions:
            azul_major_versions[major_version] = ZuluPackagesListWrap(
                packages=[])

        azul_major_versions[major_version].packages.append(pkg)

        pkg_file = os.path.join(
            UPSTREAM_DIR, AZUL_VERSIONS_DIR, "{}.json".format(pkg.package_uuid))
        if os.path.exists(pkg_file) and os.path.isfile(pkg_file):
            pass
        else:

            api_call = azulApiPackageDetail(pkg.package_uuid)
            print("Fetching Azul package manifest:", pkg.package_uuid)
            r_pkg = sess.get(api_call)
            r_pkg.raise_for_status()

            pkg_detail = ZuluPackageDetail(**r_pkg.json())
            pkg_detail.write(pkg_file)

    for major in azul_major_versions:
        major_file = os.path.join(
            UPSTREAM_DIR, AZUL_VERSIONS_DIR, "{}.json".format(major))
        azul_major_versions[major].write(major_file)


if __name__ == "__main__":
    main()
 #
