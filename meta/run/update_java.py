import os

from meta.common import upstream_path, ensure_upstream_dir, default_session
from meta.common.java import (
    BASE_DIR,
    ADOPTIUM_DIR,
    AZUL_DIR,
    ADOPTIUM_VERSIONS_DIR,
    AZUL_VERSIONS_DIR,
)
from meta.model.java import (
    ADOPTIUM_API_AVAILABLE_RELEASES,
    adoptiumAPIFeatureReleasesUrl,
    AdoptiumImageType,
    AdoptiumAPIFeatureReleasesQuery,
    AdoptiumAvailableReleases,
    AdoptiumRelease,
    AdoptiumReleases,
    azulApiPackagesUrl,
    AzulApiPackagesQuery,
    ZuluPackage,
    ZuluPackageList,
    AzulArchiveType,
    AzulReleaseStatus,
    AzulAvailabilityType,
    AzulJavaPackageType,
    azulApiPackageDetailUrl,
    ZuluPackageDetail,
    ZuluPackagesDetail,
)

UPSTREAM_DIR = upstream_path()

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
        UPSTREAM_DIR, ADOPTIUM_DIR, "available_releases.json"
    )
    available.write(available_releases_file)

    for feature in available.available_releases:
        print("Getting Manifests for Adoptium feature release:", feature)

        page_size = 10

        releases_for_feature: list[AdoptiumRelease] = []
        page = 0
        while True:
            query = AdoptiumAPIFeatureReleasesQuery(
                image_type=AdoptiumImageType.Jre, page_size=page_size, page=page
            )
            api_call = adoptiumAPIFeatureReleasesUrl(feature, query=query)
            print("Fetching JRE Page:", page, api_call)
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
        releases = AdoptiumReleases(__root__=releases_for_feature)
        feature_file = os.path.join(
            UPSTREAM_DIR, ADOPTIUM_VERSIONS_DIR, f"java{feature}.json"
        )
        releases.write(feature_file)

    print("Getting Azul Release Manifests")
    zulu_packages: list[ZuluPackage] = []
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
            page_size=page_size,
        )
        api_call = azulApiPackagesUrl(query=query)

        print("Processing Page:", page, api_call)

        r = sess.get(api_call)
        if r.status_code == 404:
            break
        else:
            r.raise_for_status()

        packages = list(ZuluPackage(**pkg) for pkg in r.json())
        zulu_packages.extend(packages)
        if len(packages) < page_size:
            break
        page += 1

    print("Total Azul Packages:", len(zulu_packages))
    packages = ZuluPackageList(__root__=zulu_packages)
    azul_manifest_file = os.path.join(UPSTREAM_DIR, AZUL_DIR, "packages.json")
    packages.write(azul_manifest_file)

    azul_major_versions: dict[int, ZuluPackagesDetail] = {}

    for _, pkg in packages:

        major_version = pkg.java_version[0]
        if major_version not in azul_major_versions:
            azul_major_versions[major_version] = ZuluPackagesDetail(__root__=[])

        pkg_file = os.path.join(
            UPSTREAM_DIR, AZUL_VERSIONS_DIR, f"{pkg.package_uuid}.json"
        )
        if os.path.exists(pkg_file) and os.path.isfile(pkg_file):
            pkg_detail = ZuluPackageDetail.parse_file(pkg_file)
            azul_major_versions[major_version].append(pkg_detail)
        else:

            api_call = azulApiPackageDetailUrl(pkg.package_uuid)
            print("Fetching Azul package manifest:", pkg.package_uuid)
            r_pkg = sess.get(api_call)
            r_pkg.raise_for_status()

            pkg_detail = ZuluPackageDetail(**r_pkg.json())
            pkg_detail.write(pkg_file)
            azul_major_versions[major_version].append(pkg_detail)

    for major in azul_major_versions:
        major_file = os.path.join(UPSTREAM_DIR, AZUL_VERSIONS_DIR, f"java{major}.json")
        azul_major_versions[major].write(major_file)


if __name__ == "__main__":
    main()
#
