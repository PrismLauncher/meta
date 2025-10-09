import copy
import datetime
import os
from typing import Optional
from functools import reduce

from meta.common import ensure_component_dir, launcher_path, upstream_path

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
    AdoptiumImageType,
    AdoptiumBinary,
    ZuluPackageList,
    ZuluPackageDetail,
    AzulJavaPackageType,
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


def mojang_component_to_major(mojang_component: MojangJavaComponent) -> int:
    match mojang_component:
        case MojangJavaComponent.JreLegacy:
            return 8
        case MojangJavaComponent.Alpha:
            return 17
        case MojangJavaComponent.Beta:
            return 17
        case MojangJavaComponent.Gamma:
            return 17
        case MojangJavaComponent.GammaSnapshot:
            return 17
        case MojangJavaComponent.Exe:
            return 0
        case MojangJavaComponent.Delta:
            return 21
        case _:
            return 0


def mojang_runtime_to_java_runtime(
    mojang_runtime: MojangJavaRuntime,
    mojang_component: MojangJavaComponent,
    runtime_os: JavaRuntimeOS,
) -> JavaRuntimeMeta:
    major, _, trail = mojang_runtime.version.name.partition("u")
    security, _, buildstr = trail.partition("-")

    if buildstr == "":
        buildstr = None

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
        buildstr=buildstr,
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
        security=(
            rls.version_data.security if rls.version_data.security is not None else 0
        ),
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


def writeJavas(javas: dict[int, list[JavaRuntimeMeta]], uid: str):
    def oldest_timestamp(a: datetime.datetime | None, b: datetime.datetime):
        if a is None or a > b:
            return b
        return a

    ensure_component_dir(uid)

    # small hack to sort the versions after major
    javas = dict(sorted(javas.items(), key=lambda item: item[0]))
    timestamps: dict[int, datetime.datetime | None] = {}
    prevDate: datetime.datetime | None = None
    for major, runtimes in javas.items():
        releaseTime = reduce(
            oldest_timestamp,
            (runtime.release_time for runtime in runtimes),
            None,
        )
        if prevDate is not None and releaseTime < prevDate:
            releaseTime = prevDate + datetime.timedelta(seconds=1)
        prevDate = releaseTime
        timestamps[major] = releaseTime

    for major, runtimes in javas.items():
        version_file = os.path.join(LAUNCHER_DIR, uid, f"java{major}.json")
        java_version = JavaRuntimeVersion(
            name=f"Java {major}",
            uid=uid,
            version=f"java{major}",
            releaseTime=timestamps.get(major),
            runtimes=runtimes,
        )
        java_version.write(version_file)

    package = MetaPackage(uid=uid, name="Java Runtimes", recommended=[])
    package.write(os.path.join(LAUNCHER_DIR, uid, "package.json"))


def main():
    javas: dict[int, list[JavaRuntimeMeta]] = {}
    extra_mojang_javas: dict[int, list[JavaRuntimeMeta]] = {}

    def add_java_runtime(runtime: JavaRuntimeMeta, major: int):
        if major not in javas:
            javas[major] = list[JavaRuntimeMeta]()
        print(f"Regestering runtime: {runtime.name} for Java {major}")
        javas[major].append(runtime)

        # only add specific versions to the list
        if (
            (
                runtime.runtime_os
                in [JavaRuntimeOS.MacOsArm64, JavaRuntimeOS.WindowsArm64]
                and major == 8
            )
            or (
                runtime.runtime_os
                in [
                    JavaRuntimeOS.WindowsArm32,
                    JavaRuntimeOS.LinuxArm32,
                    JavaRuntimeOS.LinuxArm64,
                ]
                and major in [8, 17, 21]
            )
            or (runtime.runtime_os == JavaRuntimeOS.LinuxX86 and major in [17, 21])
        ):
            if major not in extra_mojang_javas:
                extra_mojang_javas[major] = list[JavaRuntimeMeta]()
            extra_mojang_javas[major].append(runtime)

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
                    if (
                        binary.package is None
                        or binary.image_type is not AdoptiumImageType.Jre
                    ):
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
            if major < 8 or pkg_detail.java_package_type is not AzulJavaPackageType.Jre:
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

    # constructs the missing mojang javas based on adoptium or azul
    def get_mojang_extra_java(
        mojang_component: MojangJavaComponent, java_os: JavaRuntimeOS
    ) -> JavaRuntimeMeta | None:
        java_major = mojang_component_to_major(mojang_component)
        if not java_major in extra_mojang_javas:
            return None
        posible_javas = list(
            filter(lambda x: x.runtime_os == java_os, extra_mojang_javas[java_major])
        )
        if len(posible_javas) == 0:
            return None
        prefered_vendor = list(filter(lambda x: x.vendor != "azul", posible_javas))
        if len(prefered_vendor) == 0:
            prefered_vendor = posible_javas
        prefered_vendor.sort(key=lambda x: x.version, reverse=True)
        runtime = prefered_vendor[0]
        runtime.name = mojang_component
        return runtime

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
            if len(mojang_runtimes) == 0:
                if mojang_os_name in [
                    MojangJavaOsName.WindowsArm64,
                    MojangJavaOsName.MacOSArm64,
                ]:
                    if comp in [MojangJavaComponent.Alpha, MojangJavaComponent.Beta]:
                        mojang_runtimes = mojang_java_manifest[mojang_os_name][
                            MojangJavaComponent.Gamma
                        ]
                    elif (
                        comp == MojangJavaComponent.JreLegacy
                    ):  # arm version of win and mac is missing the legacy java
                        runtime = get_mojang_extra_java(comp, java_os)
                        if runtime != None:
                            add_java_runtime(runtime, mojang_component_to_major(comp))
                if (
                    mojang_os_name == MojangJavaOsName.Linuxi386
                    and comp != MojangJavaComponent.JreLegacy
                ):  # the linux x86 is missing all but legacy
                    runtime = get_mojang_extra_java(comp, java_os)
                    if runtime != None:
                        add_java_runtime(runtime, mojang_component_to_major(comp))
            for mojang_runtime in mojang_runtimes:
                if comp == MojangJavaComponent.JreLegacy:
                    major = 8
                else:
                    major = int(mojang_runtime.version.name.partition(".")[0])
                runtime = mojang_runtime_to_java_runtime(mojang_runtime, comp, java_os)
                add_java_runtime(runtime, major)
    # mojang doesn't provide any versions for the following systems so borrow info from adoptium/azul
    for java_os in [
        JavaRuntimeOS.WindowsArm32,
        JavaRuntimeOS.LinuxArm32,
        JavaRuntimeOS.LinuxArm64,
    ]:
        for comp in [
            MojangJavaComponent.JreLegacy,
            MojangJavaComponent.Alpha,
            MojangJavaComponent.Beta,
            MojangJavaComponent.Gamma,
            MojangJavaComponent.GammaSnapshot,
            MojangJavaComponent.Delta,
        ]:
            runtime = get_mojang_extra_java(comp, java_os)
            if runtime != None:
                add_java_runtime(runtime, mojang_component_to_major(comp))

    writeJavas(javas=javas, uid=JAVA_MINECRAFT_COMPONENT)
    javas = {}


if __name__ == "__main__":
    main()
