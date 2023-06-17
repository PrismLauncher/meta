import copy
import os
from typing import Optional

from meta.common import ensure_component_dir, launcher_path, upstream_path, static_path

from meta.common.java import (
    JAVA_COMPONENT,
    ADOPTIUM_DIR,
    ADOPTIUM_VERSIONS_DIR,
    AZUL_DIR,
    AZUL_VERSIONS_DIR,
)
from meta.model import MetaPackage
from meta.model.java import (
    JavaRuntimeOS,
    JavaRuntimeMap,
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

ensure_component_dir(JAVA_COMPONENT)

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
) -> JavaRuntimeMeta:
    major, _, security = mojang_runtime.version.name.partition("u")
    if major and security:
        version_parts = [int(major), 0, int(security)]
    else:
        version_parts = [int(part)
                         for part in mojang_runtime.version.name.split(".")]

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
        name=f"mojang_jre_{mojang_runtime.version.name}",
        vendor="mojang",
        url=mojang_runtime.manifest.url,
        releaseTime=mojang_runtime.version.released,
        checksum=JavaChecksumMeta(
            type=JavaChecksumType.Sha1, hash=mojang_runtime.manifest.sha1
        ),
        recommended=True,
        downloadType=JavaRuntimeDownloadType.Manifest,
        packageType=JavaPackageType.Jre,
        version=version,
    )


def adoptium_release_binary_to_java_runtime(
    rls: AdoptiumRelease, binary: AdoptiumBinary
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
        security=rls.version_data.security if rls.version_data.security is not None else 0,
        build=rls.version_data.build,
    )
    rls_name = f"{rls.vendor}_temurin_{binary.image_type}{version}"
    return JavaRuntimeMeta(
        name=rls_name,
        vendor=rls.vendor,
        url=binary.package.link,
        releaseTime=rls.timestamp,
        checksum=checksum,
        recommended=False,
        downloadType=JavaRuntimeDownloadType.Archive,
        packageType=pkg_type,
        version=version,
    )


def azul_package_to_java_runtime(pkg: ZuluPackageDetail) -> JavaRuntimeMeta:
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
        checksum = JavaChecksumMeta(
            type=JavaChecksumType.Sha256, hash=pkg.sha256_hash
        )

    return JavaRuntimeMeta(
        name=rls_name,
        vendor="azul",
        url=pkg.download_url,
        releaseTime=pkg.build_date,
        checksum=checksum,
        recommended=False,
        downloadType=JavaRuntimeDownloadType.Archive,
        packageType=pkg_type,
        version=version,
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


def ensure_one_recommended(runtimes: list[JavaRuntimeMeta]) -> Optional[JavaRuntimeMeta]:
    if len(runtimes) < 1:
        return None  # can't do anything

    recommended: Optional[JavaRuntimeMeta] = None
    found_first = False
    need_resort = False
    for runtime in runtimes:
        if runtime.recommended:
            if not found_first:
                recommended = runtime
            else:
                runtime.recommended = False
                need_resort = True

    if recommended and not need_resort:
        return recommended  # we have one recommended already

    if recommended is None:
        recommended = runtimes[0]

    def better_java_runtime(runtime: JavaRuntimeMeta):
        assert recommended is not None
        if vendor_priority(runtime.vendor) < vendor_priority(recommended.vendor):
            return False
        if pkg_type_priority(runtime.package_type) < pkg_type_priority(recommended.package_type):
            return False
        if runtime.version < recommended.version:
            return False
        if runtime.release_time < recommended.release_time:
            return False
        return True

    for runtime in runtimes:
        if better_java_runtime(runtime):
            recommended.recommended = False
            recommended = runtime
            recommended.recommended = True

    return recommended


def main():
    javas: dict[int, JavaRuntimeMap] = {}

    def ensure_javamap(major: int):
        if major not in javas:
            javas[major] = JavaRuntimeMap()

    def add_java_runtime(runtime: JavaRuntimeMeta, major: int, java_os: JavaRuntimeOS):
        ensure_javamap(major)
        print(
            f"Regestering runtime: {runtime.name} for Java {major} {java_os}")
        javas[major][java_os].append(runtime)

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
                runtime = mojang_runtime_to_java_runtime(mojang_runtime)
                add_java_runtime(runtime, major, java_os)

    print("Processing Adoptium Releases")
    adoptium_available_releases = AdoptiumAvailableReleases.parse_file(
        os.path.join(UPSTREAM_DIR, ADOPTIUM_DIR, "available_releases.json")
    )
    for major in adoptium_available_releases.available_releases:
        adoptium_releases = AdoptiumReleases.parse_file(
            os.path.join(UPSTREAM_DIR, ADOPTIUM_VERSIONS_DIR,
                         f"java{major}.json")
        )
        for _, rls in adoptium_releases:
            for binary in rls.binaries:
                if binary.package is None:
                    continue
                binary_arch = translate_arch(str(binary.architecture))
                binary_os = translate_os(str(binary.os))
                if binary_arch is None or binary_os is None:
                    print(
                        f"Ignoring release for {binary.os} {binary.architecture}")
                    continue

                java_os = JavaRuntimeOS(f"{binary_os}-{binary_arch}")
                runtime = adoptium_release_binary_to_java_runtime(rls, binary)
                add_java_runtime(runtime, major, java_os)

    print("Processing Azul Packages")
    azul_packages = ZuluPackageList.parse_file(
        os.path.join(UPSTREAM_DIR, AZUL_DIR, "packages.json")
    )
    for _, pkg in azul_packages:
        pkg_detail = ZuluPackageDetail.parse_file(
            os.path.join(UPSTREAM_DIR, AZUL_VERSIONS_DIR,
                         f"{pkg.package_uuid}.json")
        )
        major = pkg_detail.java_version[0]
        if major < 8:
            continue  # we will never need java versions less than 8

        pkg_os = translate_os(str(pkg_detail.os))
        if pkg_detail.arch == AzulArch.Arm:
            pkg_arch = translate_arch(
                f"{pkg_detail.arch}{pkg_detail.hw_bitness}")
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
        runtime = azul_package_to_java_runtime(pkg_detail)
        add_java_runtime(runtime, major, java_os)

    for major, runtimes in javas.items():
        for java_os, runtime_list in runtimes:
            print(f"Total runtimes for Java {major} {java_os}:", len(
                runtime_list))
            rec = ensure_one_recommended(runtime_list)
            if rec is not None:
                print(f"Recomending {rec.name} for Java {major} {java_os}")

        version_file = os.path.join(
            LAUNCHER_DIR, JAVA_COMPONENT, f"java{major}.json")
        java_version = JavaRuntimeVersion(name = f"Java {major}", uid = JAVA_COMPONENT, version = f"java{major}", runtimes = runtimes)
        java_version.write(version_file)

    package = MetaPackage(
        uid = JAVA_COMPONENT,
        name = "Java Runtimes",
        recommended = ["java8", "java17"]
    )
    package.write(os.path.josn(LAUNCHER_DIR, JAVA_COMPONENT, "package.json"))


if __name__ == "__main__":
    main()
