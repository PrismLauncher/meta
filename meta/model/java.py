from . import (
    MetaBase,
)
from pydantic import Field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Iterator, Iterable, NamedTuple
from collections import namedtuple
from urllib.parse import urljoin, urlencode, urlparse, urlunparse

# namedtuple to match the internal signature of urlunparse


class URLComponents(NamedTuple):
    scheme: str
    netloc: str
    url: str
    path: str
    query: str
    fragment: str


class APIQuery(MetaBase):

    def to_query(self):
        set_parts: dict[str, Any] = {}
        for key, value in self.dict().items():
            if value is not None:
                if isinstance(value, Enum):
                    set_parts[key] = value.value
                elif isinstance(value, list):
                    if len(value) > 0:
                        set_parts[key] = value
                elif isinstance(value, datetime):
                    set_parts[key] = value.isoformat()
                else:
                    set_parts[key] = value
        return urlencode(set_parts, doseq=True)


class AdoptiumJvmImpl(Enum):
    Hostspot = "hotspot"


class AdoptiumVendor(Enum):
    Eclipse = "eclipse"


class AdoptiumArchitecture(Enum):
    X64 = "x64"
    X86 = "x86"
    X32 = "x32"
    Ppc64 = "ppc64"
    Ppc64le = "ppc64le"
    S390x = "s390x"
    Aarch64 = "aarch64"
    Arm = "arm"
    Sparcv9 = "sparcv9"
    Riscv64 = "riscv64"


class AdoptiumReleaseType(Enum):
    GenralAccess = "ga"
    EarlyAccess = "ea"


class AdoptiumSortMethod(Enum):
    Default = "DEFAULT"
    Date = "DATE"


class AdoptiumSortOrder(Enum):
    Asc = "ASC"
    Desc = "DESC"


class AdoptiumImageType(Enum):
    Jdk = "jdk"
    Jre = "jre"
    Testimage = "testimage"
    Debugimage = "debugimage"
    Staticlibs = "staticlibs"
    Sources = "sources"
    Sbom = "sbom"


class AdoptiumHeapSize(Enum):
    Normal = "normal"
    Large = "large"


class AdoptiumProject(Enum):
    Jdk = "jdk"
    Valhalla = "valhalla"
    Metropolis = "metropolis"
    Jfr = "jfr"
    Shenandoah = "shenandoah"


class AdoptiumCLib(Enum):
    Musl = "musl"
    Glibc = "Glibc"


class AdoptiumOs(Enum):
    Linux = "linux"
    Windows = "windows"
    Mac = "mac"
    Solaris = "solaris"
    Aix = "aix"
    AlpineLinux = "alpine-linux"


ADOPTIUM_API_BASE = " https://api.adoptium.net"
ADOPTIUM_API_FEATURE_RELEASES = f"{ADOPTIUM_API_BASE}/v3/assets/feature_releases/{{feature_version}}/{{release_type}}"
# ?image_type={{image_type}}&heap_size={{heap_size}}&project={{project}}&vender={{vender}}&page_size={{page_size}}&page={{page}}&sort_method={{sort_method}}&sort_order={{sort_order}}
ADOPTIUM_API_AVAILABLE_RELEASES = f"{ADOPTIUM_API_BASE}/v3/info/available_releases"


class AdoptiumAPIFeatureReleasesQuery(APIQuery):
    architecture: Optional[AdoptiumArchitecture] = None
    before: Optional[datetime] = None
    c_lib: Optional[AdoptiumCLib] = None
    heap_size: Optional[AdoptiumHeapSize] = AdoptiumHeapSize.Normal
    image_type: Optional[AdoptiumImageType] = None
    jvm_impl: Optional[AdoptiumJvmImpl] = None
    os: Optional[AdoptiumOs] = None
    page_size: int = 10
    page: int = 0
    project: Optional[AdoptiumProject] = AdoptiumProject.Jdk
    sort_method:  Optional[AdoptiumSortMethod] = AdoptiumSortMethod.Default
    sort_order:  Optional[AdoptiumSortOrder] = AdoptiumSortOrder.Desc
    vender:  Optional[AdoptiumVendor] = AdoptiumVendor.Eclipse


def adoptiumAPIFeatureReleases(
        feature: int,
        release_type: AdoptiumReleaseType = AdoptiumReleaseType.GenralAccess,
        query: AdoptiumAPIFeatureReleasesQuery = AdoptiumAPIFeatureReleasesQuery()
):
    url = urlparse(ADOPTIUM_API_FEATURE_RELEASES.format(
        feature_version=feature,
        release_type=release_type.value,
    ))
    return urlunparse(url._replace(query=query.to_query()))


class AdoptiumAvailableReleases(MetaBase):
    available_releases: list[int]
    available_lts_releases: list[int]
    most_recent_lts: Optional[int]
    most_recent_feature_release: Optional[int]
    most_recent_feature_version: Optional[int]
    tip_version: Optional[int]


class AdoptiumFile(MetaBase):
    name: str
    link: str
    size: Optional[int]


class AdoptiumPackage(AdoptiumFile):
    checksum: Optional[str]
    checksum_link: Optional[str]
    signature_link: Optional[str]
    download_count: Optional[int]
    metadata_link: Optional[str]


class AdoptiumBinary(MetaBase):
    os: str
    architecture: AdoptiumArchitecture
    image_type: AdoptiumImageType
    c_lib: Optional[AdoptiumCLib]
    jvm_impl: AdoptiumJvmImpl
    package: Optional[AdoptiumPackage]
    installer: Optional[AdoptiumPackage]
    heap_size: AdoptiumHeapSize
    download_count: Optional[int]
    updated_at: datetime
    scm_ref: Optional[str]
    project: AdoptiumProject


class AdoptiumVersion(MetaBase):
    major: Optional[int]
    minor: Optional[int]
    security: Optional[int]
    patch: Optional[int]
    pre: Optional[str]
    adopt_build_number: Optional[int]
    semver: str
    openjdk_version: str
    build: Optional[int]
    optional: Optional[str]


class AdoptiumRelease(MetaBase):
    release_id: str = Field(alias="id")
    release_link: str
    release_name: str
    timestamp: datetime
    updated_at: datetime
    binaries: list[AdoptiumBinary]
    download_count: Optional[int]
    release_type: str
    vendor: AdoptiumVendor
    version_data: AdoptiumVersion
    source: Optional[AdoptiumFile]
    release_notes: Optional[AdoptiumFile]


class AdoptiumReleasesWrap(MetaBase):
    releases: list[AdoptiumRelease]


class AzulProduct(Enum):
    Zulu = "zulu"


class AzulAvailabilityType(Enum):
    SA = "SA"
    CA = "CA"
    NV = "NV"
    _LA = "LA"


class AzulJavaPackageType(Enum):
    Jdk = "jdk"
    Jre = "jre"


class AzulReleaseType(Enum):
    CPU = "CPU"
    PSU = "PSU"
    LU = "LU"


class AzulOs(Enum):
    Linux = "linux"
    Macos = "macos"
    Qnx = "qnx"
    Windows = "windows"
    Solaris = "solaris"


class AzulLibCType(Enum):
    Glibc = "glibc"
    Uclibc = "uclibc"
    Musl = "musl"


class AzulCPUGen(Enum):
    V5 = "v5"
    V6kV6kz = "v6k_v6kz"
    V6t2 = "v6t2"
    V7 = "v7"
    V8 = "v8"


class AzulArch(Enum):
    Arm = "arm"
    X86 = "x86"
    Mips = "mips"
    Ppc = "ppc"
    Sparcv9 = "sparcv9"
    Sparc = "sparc"


class AzulHwBitness(Enum):
    X32 = 32
    X64 = 64


class AzulAbi(Enum):
    HardFloat = "hard_float"
    SoftFloat = "soft_float"
    Spe = "spe"
    Any = "any"


class AzulArchiveType(Enum):
    Deb = "deb"
    Rpm = "rpm"
    Dmg = "dmg"
    Targz = "tar.gz"
    Zip = "zip"
    Cab = "cab"
    Msi = "msi"


class AzulReleaseStatus(Enum):
    Eval = "eval"
    Ea = "ea"
    Ga = "ga"
    Both = "both"


class AzulSupportTerm(Enum):
    Sts = "sts"
    Mts = "mts"
    Lts = "lts"


class AzulCertifications(Enum):
    Tck = "tck"
    _Aqavit = "aqavit"
    none = "none"


class AzulSignatureType(Enum):
    Openpgp = "openpgp"


class AzulOsQueryParam(Enum):
    Macos = "macos"
    Windows = "windows"
    Linux = "linux"
    LinuxMusl = "linux-musl"
    LinuxGlibc = "linux-glibc"
    Qnx = "qnx"
    Solaris = "solaris"


class AzulArchQueryParam(Enum):
    X86 = "x86"
    X64 = "x64"
    Amd64 = "amd64"
    I686 = "i686"
    Arm = "arm"
    Aarch64 = "aarch64"
    Aarch32 = "aarch32"
    Aarch32sf = "aarch32sf"
    Aarch32hf = "aarch32hf"
    Ppc = "ppc"
    Ppc64 = "ppc64"
    Ppc64hf = "ppc64hf"
    Ppc32 = "ppc32"
    Ppc32spe = "ppc32spe"
    Ppc32hf = "ppc32hf"
    Sparc = "sparc"
    Sparc32 = "sparc32"
    Sparcv9 = "sparcv9"
    Sparcv9_64 = "sparcv9-64"


AZUL_API_BASE = "https://api.azul.com/metadata/v1"
AZUL_API_PACKAGES = f"{AZUL_API_BASE}/zulu/packages/"
AZUL_API_PACKAGE_DETAIL = f"{AZUL_API_BASE}/zulu/packages/{{package_uuid}}"


class AzulApiPackagesQuery(APIQuery):
    java_version: Optional[str] = None
    os: Optional[AzulOsQueryParam] = None
    arch: Optional[AzulArchQueryParam] = None
    archive_type: Optional[AzulArchiveType] = None
    java_package_type: Optional[AzulJavaPackageType] = None
    javafx_bundled: Optional[bool] = None
    crac_supported: Optional[bool] = None
    support_term: Optional[AzulSupportTerm] = None
    release_type: Optional[AzulReleaseType] = None
    latest: Optional[bool] = None
    distro_version: Optional[str] = None
    java_package_features: list[str] = []
    release_status: Optional[AzulReleaseStatus] = None
    availability_types: list[AzulAvailabilityType] = None
    certifications: list[AzulCertifications] = None
    include_fields: list[str] = []
    page: int = 0
    page_size: int = 100


def azulApiPackages(query: AzulApiPackagesQuery = AzulApiPackagesQuery()):
    url = urlparse(AZUL_API_PACKAGES)
    return urlunparse(url._replace(query=query.to_query()))


def azulApiPackageDetail(package_uuid: str):
    return AZUL_API_PACKAGE_DETAIL.format(package_uuid=package_uuid)


class ZuluSignatureDetail(MetaBase):
    type: AzulSignatureType
    url: str
    details: dict[str, Any]
    signature_index: int
    signature: str


class ZuluPackageDetail(MetaBase):
    package_uuid: str
    name: Optional[str]
    md5_hash: Optional[str]
    sha256_hash: Optional[str]
    build_date: datetime
    last_modified: datetime
    download_url: str
    product: AzulProduct
    availability_type: AzulAvailabilityType
    java_version: list[int]
    openjdk_build_number: Optional[int]
    java_package_type: AzulJavaPackageType
    javafx_bundled: bool
    release_type: AzulReleaseType
    os: AzulOs
    lib_c_type: Optional[AzulLibCType]
    cpu_gen: Optional[list[AzulCPUGen]]
    arch: AzulArch
    hw_bitness: AzulHwBitness
    abi: AzulAbi
    archive_type: AzulArchiveType
    release_status: AzulReleaseStatus
    support_term: AzulSupportTerm
    certifications: Optional[list[AzulCertifications]]
    latest: Optional[bool]
    size: int
    distro_version: list[int]
    signatures: list[ZuluSignatureDetail]


class ZuluPackageList(MetaBase):
    package_uuid: str
    name: Optional[str]
    java_version: list[int]
    openjdk_build_number: Optional[int]
    latest: Optional[bool]
    download_url: str
    product: Optional[AzulProduct]
    distro_version: list[int]
    availability_type: Optional[AzulAvailabilityType]


class ZuluPackagesListWrap(MetaBase):
    packages: list[ZuluPackageList]


class ZuluPackagesDetailListWrap(MetaBase):
    packages: list[ZuluPackageDetail]
