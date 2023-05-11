import copy
import hashlib
import os
from collections import defaultdict, namedtuple
from operator import attrgetter
from pprint import pprint
from packaging import version as pversion
from typing import Optional, List

from meta.common import ensure_component_dir, launcher_path, upstream_path, static_path

from meta.common.java import (
    JAVA_COMPONENT,
    ADOPTIUM_DIR,
    ADOPTIUM_VERSIONS_DIR,
    AZUL_DIR,
    AZUL_VERSIONS_DIR
)
from meta.model.java import (
    JavaRuntimeOS,
    JavaRuntimeMap,
    JavaRuntimeMeta,
    JavaVersionMeta,
    JavaChecksumMeta,
    JavaChecksumType,
    JavaRuntimeDownloadType,
    AdoptiumAvailableReleases,
    AdoptiumReleases,
    AdoptiumRelease,
    AdoptiumBinary,
    ZuluPackages,
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

MOJANG_JAVA_OS_NAMES = [
    "gamecore",
    "linux",
    "linux-i386",
    "mac-os",
    "mac-os-arm64",
    "windows-arm64",
    "windows-x64",
    "windows-x86",
]

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
    "arm": "arm32"
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
    if mojang_os == MojangJavaOsName.Linux:
        return JavaRuntimeOS.LinuxX64
    elif mojang_os == MojangJavaOsName.Linuxi386:
        return JavaRuntimeOS.LinuxX86
    elif mojang_os == MojangJavaOsName.MacOs:
        return JavaRuntimeOS.MacOsX64
    elif mojang_os == MojangJavaOsName.MacOSArm64:
        return JavaRuntimeOS.MacOsArm64
    elif mojang_os == MojangJavaOsName.WindowsArm64:
        return JavaRuntimeOS.WindowsArm64
    elif mojang_os == MojangJavaOsName.WindowsX64:
        return JavaRuntimeOS.WindowsX64
    elif mojang_os == MojangJavaOsName.WindowsX86:
        return JavaRuntimeOS.WindowsX86
    else:
        return JavaRuntimeOS.Unknown


def mojang_runtime_to_java_runtime(mojang_runtime: MojangJavaRuntime) -> JavaRuntimeMeta:
    return JavaRuntimeMeta(
        name=f"mojang_jre_{mojang_runtime.version.name}",
        vender="mojang",
        url=mojang_runtime.manifest.url,
        release_time=mojang_runtime.version.released,
        checksum=JavaChecksumMeta(
            type=JavaChecksumType.Sha1,
            hash=mojang_runtime.manifest.sha1),
        recomended=True,
        download_type=JavaRuntimeDownloadType.Manifest)

def adoptium_release_binary_to_java_runtime(rls: AdoptiumRelease, binary: AdoptiumBinary) -> JavaRuntimeMeta:
    version = JavaVersionMeta(
        major=rls.version_data.major,
        minor=rls.version_data.minor,
        security=rls.version_data.security,
        build=rls.version_data.build
    )
    rls_name = f"{rls.vendor}_temurin_{binary.image_type}{version}"
    return JavaRuntimeMeta(
        name=rls_name,
        vender=rls.vendor,
        url=binary.package.link,
        release_time=rls.timestamp,
        checksum=JavaChecksumMeta(
            type=JavaChecksumType.Sha256,
            hash=binary.package.checksum),
        recomended=False,
        download_type=JavaRuntimeDownloadType.Archive
    )

def azul_package_to_java_runtime(pkg: ZuluPackageDetail) -> JavaRuntimeMeta:
    version_parts = copy.copy(pkg.java_version)
    while len(version_parts) < 4:
        version_parts.append(None)
    
    version = JavaVersionMeta(
        major=version_parts[0],
        minor=version_parts[1],
        security=version_parts[2],
        build=version_parts[3]
    )
    
    rls_name = f"azul_{pkg.product}_{pkg.java_package_type}{version}"
    
    return JavaRuntimeMeta(
        name=rls_name,
        vender="azul",
        url=pkg.download_url,
        release_time=pkg.build_date,
        checksum=JavaChecksumMeta(
            type=JavaChecksumType.Sha256,
            hash=pkg.sha256_hash),
        recomended=False,
        download_type=JavaRuntimeDownloadType.Archive
    )

def main():
    
    javas: dict[int, JavaRuntimeMap] = {}
    
    def ensure_javamap(major: int):
        if major not in javas:
            javas[major] = JavaRuntimeMap()
            
    def add_java_runtime(runtime: JavaRuntimeMeta, major: int, java_os: JavaRuntimeOS):
        ensure_javamap(major)
        print(f"Regestering runtime: {runtime.name} for Java {major} {java_os}")
        javas[major][java_os].append(runtime)
    
    print("Processing Mojang Javas")
    mojang_java_manifest = JavaIndex.parse_file(
        os.path.join(UPSTREAM_DIR, JAVA_MANIFEST_FILE)
    )
    for mojang_os_name in mojang_java_manifest:
        if mojang_os_name == MojangJavaOsName.Gamecore:
            continue
        java_os = mojang_os_to_java_os(mojang_os_name)
        for comp in mojang_java_manifest[mojang_os_name]:
            mojang_runtimes = mojang_java_manifest[mojang_os_name][comp]
            for mojang_runtime in mojang_runtimes:
                if comp == MojangJavaComponent.JreLegacy:
                    major = 8
                else:
                    major = int(mojang_runtime.version.name.partition('.')[0])
                runtime = mojang_runtime_to_java_runtime(mojang_runtime)
                add_java_runtime(runtime, major, java_os)
                
    print("Processing Adoptium Releases")
    adoptium_available_releases = AdoptiumAvailableReleases.parse_file(
        os.path.join(UPSTREAM_DIR, ADOPTIUM_DIR, "available_releases.json")
    )
    for major in adoptium_available_releases.available_releases:
        adoptium_releases = AdoptiumReleases.parse_file(
            os.path.join(UPSTREAM_DIR, ADOPTIUM_VERSIONS_DIR, f"java{major}.json")
        )
        for rls in adoptium_releases:
            for binary in rls.binaries:
                if binary.package is None:
                    continue
                binary_arch = translate_arch(str(binary.architecture))
                binary_os = translate_os(str(binary.os))
                if binary_arch is None or binary_os is None:
                    print(f"Ignoring release for {binary.os} {binary.architecture}")
                    continue
                    
                java_os = JavaRuntimeOS(f"{binary_os}-{binary_arch}")
                runtime = adoptium_release_binary_to_java_runtime(rls, binary)
                add_java_runtime(runtime, major, java_os)
    
    print("Processing Azul Packages")
    azul_packages = ZuluPackages.parse_file(
        os.path.join(UPSTREAM_DIR, AZUL_DIR, "packages.json")
    )
    for pkg in azul_packages:
        pkg_detail = ZuluPackageDetail.parse_file(
            os.path.join(UPSTREAM_DIR, AZUL_VERSIONS_DIR, f"{pkg.package_uuid}.json")
        )
        major =  pkg_detail.java_version[0]
        pkg_os = translate_os(str(pkg_detail.os))
        if pkg_detail.arch == AzulArch.Arm:   
            pkg_arch = translate_arch(f"{pkg_detail.arch}{pkg_detail.hw_bitness}")
        elif  pkg_detail.arch == AzulArch.X86:
            pkg_arch = translate_arch(int(pkg_detail.hw_bitness))
        else:
            pkg_arch = None
        if pkg_arch is None or pkg_os is None:
            print(f"Ignoring release for {pkg_detail.os} {pkg_detail.arch}_{pkg_detail.hw_bitness}")
            continue
        
        java_os = JavaRuntimeOS(f"{pkg_os}-{pkg_arch}")
        runtime = azul_package_to_java_runtime(pkg_detail)
        add_java_runtime(runtime, major, java_os)
    
    for major, runtimes in javas.items():
        for java_os in runtimes:
            print(f"Total runtimes for Java {major} {java_os}:", len(runtimes[java_os]))
        runtimes_file = os.path.join(LAUNCHER_DIR, JAVA_COMPONENT, f"java{major}.json")
        runtimes.write(runtimes_file)
        

if __name__ == "__main__":
    main()
