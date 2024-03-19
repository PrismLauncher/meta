import copy
import datetime
import os
from typing import Optional
from functools import reduce

from meta.common import ensure_component_dir, launcher_path, upstream_path, static_path

from meta.common.java import (
    JAVA_MINECRAFT_COMPONENT,
    JAVA_ADOPTIUM_COMPONENT,
    JAVA_AZUL_COMPONENT,
    ADOPTIUM_DIR,
    ADOPTIUM_VERSIONS_DIR,
    AZUL_DIR,
    AZUL_VERSIONS_DIR,
)
from meta.model import MetaPackage
from meta.model.java import (
    JavaRuntimeOS,
    JavaRuntimeVersion,
    JavaRuntimeMeta,
    JavaVersionMeta,
    JavaPackageType,
    JavaChecksumMeta,
    JavaChecksumType,
    JavaRuntimeDownloadType,
    AdoptiumAvailableReleases,
    AdoptiumReleases,
    AdoptiumRelease,
    AdoptiumBinary,
    ZuluPackageList,
    ZuluPackageDetail,
    AzulArch,
)

from meta.common.mojang import (
    JAVA_MANIFEST_FILE,
)

from meta.model.mojang import (
    JavaIndex,
    MojangJavaComponent,
    MojangJavaOsName,
    MojangJavaRuntime,
)

LAUNCHER_DIR = launcher_path()
UPSTREAM_DIR = upstream_path()
STATIC_DIR = static_path()


MOJANG_OS_ARCHITECTURES = [
    "x64",
    "x86",
    "arm64",
    "arm32",
]

MOJANG_OS_ARCHITECTURE_TRANSLATIONS = {
    64: "x64",
    32: "x86",
    "x32": "x86",
    "i386": "x86",
    "aarch64": "arm64",
    "x86_64": "x64",
    "arm": "arm32",
}


def translate_arch(arch: str | int):
    if isinstance(arch, str):
        arch = arch.lower()
    if arch in MOJANG_OS_ARCHITECTURES:
        return arch
    elif arch in MOJANG_OS_ARCHITECTURE_TRANSLATIONS:
        return MOJANG_OS_ARCHITECTURE_TRANSLATIONS[arch]
    else:
        return None


MOJANG_OS_NAMES = [
    "mac-os",
    "linux",
    "windows",
]

MOJANG_OS_TRANSLATIONS = {
    "osx": "mac-os",
    "mac": "mac-os",
    "macos": "mac-os",
}


def translate_os(os: str):
    os = os.lower()
    if os in MOJANG_OS_NAMES:
        return os
    elif os in MOJANG_OS_TRANSLATIONS:
        return MOJANG_OS_TRANSLATIONS[os]
    else:
        return None


def mojang_os_to_java_os(mojang_os: MojangJavaOsName) -> JavaRuntimeOS:
    match mojang_os:
        case MojangJavaOsName.Linux:
            return JavaRuntimeOS.LinuxX64
        case MojangJavaOsName.Linuxi386:
            return JavaRuntimeOS.LinuxX86
        case MojangJavaOsName.MacOs:
            return JavaRuntimeOS.MacOsX64
        case MojangJavaOsName.MacOSArm64:
            return JavaRuntimeOS.MacOsArm64
        case MojangJavaOsName.WindowsArm64:
            return JavaRuntimeOS.WindowsArm64
        case MojangJavaOsName.WindowsX64:
            return JavaRuntimeOS.WindowsX64
        case MojangJavaOsName.WindowsX86:
            return JavaRuntimeOS.WindowsX86
        case _:
            return JavaRuntimeOS.Unknown


def mojang_runtime_to_java_runtime(
    mojang_runtime: MojangJavaRuntime,
    mojang_component: MojangJavaComponent,
    runtime_os: JavaRuntimeOS,
) -> JavaRuntimeMeta:
    major, _, security = mojang_runtime.version.name.partition("u")
    if major and security:
        version_parts = [int(major), 0, int(security)]
    else:
        version_parts = [int(part) for part in mojang_runtime.version.name.split(".")]

    while len(version_parts) < 3:
        version_parts.append(0)

    build = None
    if len(version_parts) >= 4:
        build = version_parts[3]

    version = JavaVersionMeta(
        major=version_parts[0],
        minor=version_parts[1],
        security=version_parts[2],
        build=build,
        name=mojang_runtime.version.name,
    )
    return JavaRuntimeMeta(
        name=mojang_component,
        vendor="mojang",
        url=mojang_runtime.manifest.url,
        releaseTime=mojang_runtime.version.released,
        checksum=JavaChecksumMeta(
            type=JavaChecksumType.Sha1, hash=mojang_runtime.manifest.sha1
        ),
        downloadType=JavaRuntimeDownloadType.Manifest,
        packageType=JavaPackageType.Jre,
        version=version,
        runtime_os=runtime_os,
    )


def adoptium_release_binary_to_java_runtime(
    rls: AdoptiumRelease,
    binary: AdoptiumBinary,
    runtime_os: JavaRuntimeOS,
) -> JavaRuntimeMeta:
    assert binary.package is not None

    checksum = None
    if binary.package.checksum is not None:
        checksum = JavaChecksumMeta(
            type=JavaChecksumType.Sha256, hash=binary.package.checksum
        )

    pkg_type = JavaPackageType(str(binary.image_type))

    version = JavaVersionMeta(
        major=rls.version_data.major if rls.version_data.major is not None else 0,
        minor=rls.version_data.minor if rls.version_data.minor is not None else 0,
        security=rls.version_data.security
        if rls.version_data.security is not None
        else 0,
        build=rls.version_data.build,
    )
    rls_name = f"{rls.vendor}_temurin_{binary.image_type}{version}"
    return JavaRuntimeMeta(
        name=rls_name,
        vendor=rls.vendor,
        url=binary.package.link,
        releaseTime=rls.timestamp,
        checksum=checksum,
        downloadType=JavaRuntimeDownloadType.Archive,
        packageType=pkg_type,
        version=version,
        runtime_os=runtime_os,
    )


def azul_package_to_java_runtime(
    pkg: ZuluPackageDetail, runtime_os: JavaRuntimeOS
) -> JavaRuntimeMeta:
    version_parts = copy.copy(pkg.java_version)

    build = None
    while len(version_parts) < 3:
        version_parts.append(0)

    if len(version_parts) >= 4:
        build = version_parts[3]

    version = JavaVersionMeta(
        major=version_parts[0],
        minor=version_parts[1],
        security=version_parts[2],
        build=build,
    )

    pkg_type = JavaPackageType(str(pkg.java_package_type))

    rls_name = f"azul_{pkg.product}_{pkg.java_package_type}{version}"

    checksum = None
    if pkg.sha256_hash is not None:
        checksum = JavaChecksumMeta(type=JavaChecksumType.Sha256, hash=pkg.sha256_hash)

    return JavaRuntimeMeta(
        name=rls_name,
        vendor="azul",
        url=pkg.download_url,
        releaseTime=pkg.build_date,
        checksum=checksum,
        downloadType=JavaRuntimeDownloadType.Archive,
        packageType=pkg_type,
        version=version,
        runtime_os=runtime_os,
    )


PREFERED_VENDOR_ORDER = ["mojang", "eclipse", "azul"]

__PREFERED_VENDOR_ORDER = list(reversed(PREFERED_VENDOR_ORDER))


def vendor_priority(vendor: str) -> int:
    """Get a numeric priority for a given vendor

    Args:
        vendor (str): the vendor to check

    Returns:
        int: how preferable the vendor is, the higher the better
    """
    if vendor not in PREFERED_VENDOR_ORDER:
        return -1
    return __PREFERED_VENDOR_ORDER.index(vendor)


def pkg_type_priority(pkg_type: JavaPackageType) -> int:
    match pkg_type:
        case JavaPackageType.Jre:
            return 2
        case JavaPackageType.Jdk:
            return 1
    return -1


def writeJavas(javas: dict[int, list[JavaRuntimeMeta]], uid: str):
    ensure_component_dir(uid)
    for major, runtimes in javas.items():

        def newest_timestamp(a: datetime.datetime | None, b: datetime.datetime):
            if a is None or a < b:
                return b
            return a

        version_file = os.path.join(LAUNCHER_DIR, uid, f"java{major}.json")
        java_version = JavaRuntimeVersion(
            name=f"Java {major}",
            uid=uid,
            version=f"java{major}",
            releaseTime=reduce(
                newest_timestamp,
                (runtime.release_time for runtime in runtimes),
                None,
            ),
            runtimes=runtimes,
        )
        java_version.write(version_file)

    package = MetaPackage(uid=uid, name="Java Runtimes", recommended=[])
    package.write(os.path.join(LAUNCHER_DIR, uid, "package.json"))


def main():
    javas: dict[int, list[JavaRuntimeMeta]] = {}

    def add_java_runtime(runtime: JavaRuntimeMeta, major: int):
        if major not in javas:
            javas[major] = list[JavaRuntimeMeta]()
        print(f"Regestering runtime: {runtime.name} for Java {major}")
        javas[major].append(runtime)

    print("Processing Mojang Javas")
    mojang_java_manifest = JavaIndex.parse_file(
        os.path.join(UPSTREAM_DIR, JAVA_MANIFEST_FILE)
    )
    for mojang_os_name in mojang_java_manifest:
        if mojang_os_name == MojangJavaOsName.Gamecore:
            continue  # empty
        java_os = mojang_os_to_java_os(mojang_os_name)
        for comp in mojang_java_manifest[mojang_os_name]:
            if comp == MojangJavaComponent.Exe:
                continue  # doesn't appear to be used and not marked with a full verison so I don't trust it
            mojang_runtimes = mojang_java_manifest[mojang_os_name][comp]
            for mojang_runtime in mojang_runtimes:
                if comp == MojangJavaComponent.JreLegacy:
                    major = 8
                else:
                    major = int(mojang_runtime.version.name.partition(".")[0])
                runtime = mojang_runtime_to_java_runtime(mojang_runtime, comp, java_os)
                add_java_runtime(runtime, major)

    writeJavas(javas=javas, uid=JAVA_MINECRAFT_COMPONENT)
    javas = {}

    print("Processing Adoptium Releases")
    adoptium_path = os.path.join(UPSTREAM_DIR, ADOPTIUM_DIR, "available_releases.json")
    if os.path.exists(adoptium_path):
        adoptium_available_releases = AdoptiumAvailableReleases.parse_file(
            adoptium_path
        )
        for major in adoptium_available_releases.available_releases:
            adoptium_releases = AdoptiumReleases.parse_file(
                os.path.join(UPSTREAM_DIR, ADOPTIUM_VERSIONS_DIR, f"java{major}.json")
            )
            for _, rls in adoptium_releases:
                for binary in rls.binaries:
                    if binary.package is None:
                        continue
                    binary_arch = translate_arch(str(binary.architecture))
                    binary_os = translate_os(str(binary.os))
                    if binary_arch is None or binary_os is None:
                        print(f"Ignoring release for {binary.os} {binary.architecture}")
                        continue

                    java_os = JavaRuntimeOS(f"{binary_os}-{binary_arch}")
                    runtime = adoptium_release_binary_to_java_runtime(
                        rls, binary, java_os
                    )
                    add_java_runtime(runtime, major)

    writeJavas(javas=javas, uid=JAVA_ADOPTIUM_COMPONENT)
    javas = {}
    print("Processing Azul Packages")
    azul_path = os.path.join(UPSTREAM_DIR, AZUL_DIR, "packages.json")
    if os.path.exists(azul_path):
        azul_packages = ZuluPackageList.parse_file(azul_path)
        for _, pkg in azul_packages:
            pkg_detail = ZuluPackageDetail.parse_file(
                os.path.join(
                    UPSTREAM_DIR, AZUL_VERSIONS_DIR, f"{pkg.package_uuid}.json"
                )
            )
            major = pkg_detail.java_version[0]
            if major < 8:
                continue  # we will never need java versions less than 8

            pkg_os = translate_os(str(pkg_detail.os))
            if pkg_detail.arch == AzulArch.Arm:
                pkg_arch = translate_arch(f"{pkg_detail.arch}{pkg_detail.hw_bitness}")
            elif pkg_detail.arch == AzulArch.X86:
                pkg_arch = translate_arch(int(pkg_detail.hw_bitness))
            else:
                pkg_arch = None
            if pkg_arch is None or pkg_os is None:
                print(
                    f"Ignoring release for {pkg_detail.os} {pkg_detail.arch}_{pkg_detail.hw_bitness}"
                )
                continue

            java_os = JavaRuntimeOS(f"{pkg_os}-{pkg_arch}")
            runtime = azul_package_to_java_runtime(pkg_detail, java_os)
            add_java_runtime(runtime, major)
    writeJavas(javas=javas, uid=JAVA_AZUL_COMPONENT)
    javas = {}


if __name__ == "__main__":
    main()
