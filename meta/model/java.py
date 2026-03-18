from . import (
    MetaBase,
    MetaVersion,
    Versioned,
)
from pydantic import Field
from datetime import datetime
from enum import IntEnum, Enum
from .enum import StrEnum
from typing import Optional, Any, NamedTuple, Generator
from urllib.parse import urlencode, urlparse, urlunparse
from functools import total_ordering

# namedtuple to match the internal signature of urlunparse


class JavaRuntimeOS(StrEnum):
    MacOsX64 = "mac-os-x64"
    MacOsX86 = "mac-os-x86"  # rare
    MacOsArm64 = "mac-os-arm64"
    # MacOsArm32 = "mac-os-arm32" # doesn't exist
    LinuxX64 = "linux-x64"
    LinuxX86 = "linux-x86"
    LinuxArm64 = "linux-arm64"
    LinuxArm32 = "linux-arm32"
    LinuxRiscv64 = "linux-riscv64"
    WindowsX64 = "windows-x64"
    WindowsX86 = "windows-x86"
    WindowsArm64 = "windows-arm64"
    WindowsArm32 = "windows-arm32"
    Unknown = "unknown"


class JavaRuntimeDownloadType(StrEnum):
    Manifest = "manifest"
    Archive = "archive"


@total_ordering
class JavaVersionMeta(MetaBase):
    major: int
    minor: int
    security: int
    build: Optional[int] = None
    buildstr: Optional[str] = None
    name: Optional[str] = None

    def __str__(self):
        ver = f"{self.major}.{self.minor}.{self.security}"
        if self.build is not None:
            ver = f"{ver}+{self.build}"
        if self.buildstr is not None:
            ver = f"{ver}-{self.buildstr}"
        return ver

    def to_tuple(self):
        build = 0
        if self.build is not None:
            build = self.build
        return (self.major, self.minor, self.security, build, self.buildstr)

    def __eq__(self, other: Any):
        return self.to_tuple() == other.to_tuple()

    def __lt__(self, other: "JavaVersionMeta"):
        return self.to_tuple() < other.to_tuple()


class JavaChecksumType(StrEnum):
    Sha1 = "sha1"
    Sha256 = "sha256"


class JavaChecksumMeta(MetaBase):
    type: JavaChecksumType
    hash: str


class JavaPackageType(StrEnum):
    Jre = "jre"
    Jdk = "jdk"


class JavaRuntimeMeta(MetaBase):
    name: str
    vendor: str
    url: str
    release_time: datetime = Field(alias="releaseTime")
    checksum: Optional[JavaChecksumMeta]
    download_type: JavaRuntimeDownloadType = Field(alias="downloadType")
    package_type: JavaPackageType = Field(alias="packageType")
    version: JavaVersionMeta
    runtime_os: JavaRuntimeOS = Field(alias="runtimeOS")


class JavaRuntimeVersion(MetaVersion):
    runtimes: list[JavaRuntimeMeta]


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
                    if len(value) > 0:  # type: ignore
                        set_parts[key] = value
                elif isinstance(value, datetime):
                    set_parts[key] = value.isoformat()
                else:
                    set_parts[key] = value
        return urlencode(set_parts, doseq=True)


# Adoptx refers to both Adoptium (Eclipse Temurin) and AdoptOpenJDK (IBM Semeru Runtime Open Edition)
class AdoptxJvmImpl(StrEnum):
    Hotspot = "hotspot"
    OpenJ9 = "openj9"


class AdoptxVendor(StrEnum):
    Eclipse = "eclipse"
    Ibm = "ibm"


class AdoptxArchitecture(StrEnum):
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


class AdoptxReleaseType(StrEnum):
    GeneralAccess = "ga"
    EarlyAccess = "ea"


class AdoptxSortMethod(StrEnum):
    Default = "DEFAULT"
    Date = "DATE"


class AdoptxSortOrder(StrEnum):
    Asc = "ASC"
    Desc = "DESC"


class AdoptxImageType(StrEnum):
    Jdk = "jdk"
    Jre = "jre"
    Testimage = "testimage"
    Debugimage = "debugimage"
    Staticlibs = "staticlibs"
    Sources = "sources"
    Sbom = "sbom"


class AdoptxHeapSize(StrEnum):
    Normal = "normal"
    Large = "large"


class AdoptxProject(StrEnum):
    Jdk = "jdk"
    Valhalla = "valhalla"
    Metropolis = "metropolis"
    Jfr = "jfr"
    Shenandoah = "shenandoah"


class AdoptxCLib(StrEnum):
    Musl = "musl"
    Glibc = "glibc"


class AdoptxOs(StrEnum):
    Linux = "linux"
    Windows = "windows"
    Mac = "mac"
    Solaris = "solaris"
    Aix = "aix"
    AlpineLinux = "alpine-linux"


ADOPTIUM_API_BASE = "https://api.adoptium.net"
OPENJ9_API_BASE = " https://api.adoptopenjdk.net"
ADOPTX_API_FEATURE_RELEASES = (
    f"{{base_url}}/v3/assets/feature_releases/{{feature_version}}/{{release_type}}"
)
# ?image_type={{image_type}}&heap_size={{heap_size}}&project={{project}}&vendor={{vendor}}&page_size={{page_size}}&page={{page}}&sort_method={{sort_method}}&sort_order={{sort_order}}
ADOPTX_API_AVAILABLE_RELEASES = f"{{base_url}}/v3/info/available_releases"


class AdoptxAPIFeatureReleasesQuery(APIQuery):
    architecture: Optional[AdoptxArchitecture] = None
    before: Optional[datetime] = None
    c_lib: Optional[AdoptxCLib] = None
    heap_size: Optional[AdoptxHeapSize] = AdoptxHeapSize.Normal
    image_type: Optional[AdoptxImageType] = None
    jvm_impl: Optional[AdoptxJvmImpl] = None
    os: Optional[AdoptxOs] = None
    vendor: Optional[AdoptxVendor] = None
    page_size: int = 10
    page: int = 0
    project: Optional[AdoptxProject] = AdoptxProject.Jdk
    sort_method: Optional[AdoptxSortMethod] = AdoptxSortMethod.Default
    sort_order: Optional[AdoptxSortOrder] = AdoptxSortOrder.Desc


def adoptxAPIFeatureReleasesUrl(
    base_url: str,
    feature_version: int,
    release_type: AdoptxReleaseType = AdoptxReleaseType.GeneralAccess,
    query: AdoptxAPIFeatureReleasesQuery = AdoptxAPIFeatureReleasesQuery(),
):
    url = urlparse(
        ADOPTX_API_FEATURE_RELEASES.format(
            base_url=base_url,
            feature_version=feature_version,
            release_type=release_type.value,
        )
    )
    return urlunparse(url._replace(query=query.to_query()))


def adoptiumAPIFeatureReleasesUrl(
    feature_version: int,
    release_type: AdoptxReleaseType = AdoptxReleaseType.GeneralAccess,
    query: AdoptxAPIFeatureReleasesQuery = AdoptxAPIFeatureReleasesQuery(),
):
    return adoptxAPIFeatureReleasesUrl(
        feature_version=feature_version,
        release_type=release_type,
        query=query,
        base_url=ADOPTIUM_API_BASE,
    )


def openj9APIFeatureReleasesUrl(
    feature_version: int,
    release_type: AdoptxReleaseType = AdoptxReleaseType.GeneralAccess,
    query: AdoptxAPIFeatureReleasesQuery = AdoptxAPIFeatureReleasesQuery(),
):
    return adoptxAPIFeatureReleasesUrl(
        feature_version=feature_version,
        release_type=release_type,
        query=query,
        base_url=OPENJ9_API_BASE,
    )


class AdoptxAvailableReleases(MetaBase):
    available_releases: list[int]
    available_lts_releases: list[int]
    most_recent_lts: Optional[int]
    most_recent_feature_release: Optional[int]
    most_recent_feature_version: Optional[int]
    tip_version: Optional[int]


class AdoptxFile(MetaBase):
    name: str
    link: str
    size: Optional[int]


class AdoptxPackage(AdoptxFile):
    checksum: Optional[str]
    checksum_link: Optional[str]
    signature_link: Optional[str]
    metadata_link: Optional[str]
    # we intentionally omit download_count


class AdoptxBinary(MetaBase):
    os: str
    architecture: AdoptxArchitecture
    image_type: AdoptxImageType
    c_lib: Optional[AdoptxCLib]
    jvm_impl: AdoptxJvmImpl
    package: Optional[AdoptxPackage]
    installer: Optional[AdoptxPackage]
    heap_size: AdoptxHeapSize
    updated_at: datetime
    scm_ref: Optional[str]
    project: AdoptxProject
    # we intentionally omit download_count


class AdoptxVersion(MetaBase):
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


class AdoptxRelease(MetaBase):
    release_id: str = Field(alias="id")
    release_link: str
    release_name: str
    timestamp: datetime
    updated_at: datetime
    binaries: list[AdoptxBinary]
    release_type: str
    vendor: AdoptxVendor
    version_data: AdoptxVersion
    source: Optional[AdoptxFile]
    release_notes: Optional[AdoptxFile]
    # we intentionally omit download_count


class AdoptxReleases(MetaBase):
    __root__: list[AdoptxRelease]

    def __iter__(self) -> Generator[tuple[str, AdoptxRelease], None, None]:
        yield from ((str(i), val) for i, val in enumerate(self.__root__))

    def __getitem__(self, item: int) -> AdoptxRelease:
        return self.__root__[item]

    def append(self, rls: AdoptxRelease):
        self.__root__.append(rls)


class AzulProduct(StrEnum):
    Zulu = "zulu"


class AzulAvailabilityType(StrEnum):
    SA = "SA"
    CA = "CA"
    NV = "NV"
    _LA = "LA"


class AzulJavaPackageType(StrEnum):
    Jdk = "jdk"
    Jre = "jre"


class AzulReleaseType(StrEnum):
    CPU = "CPU"
    PSU = "PSU"
    LU = "LU"


class AzulOs(StrEnum):
    Linux = "linux"
    Macos = "macos"
    Qnx = "qnx"
    Windows = "windows"
    Solaris = "solaris"


class AzulLibCType(StrEnum):
    Glibc = "glibc"
    Uclibc = "uclibc"
    Musl = "musl"


class AzulCPUGen(StrEnum):
    V5 = "v5"
    V6kV6kz = "v6k_v6kz"
    V6t2 = "v6t2"
    V7 = "v7"
    V8 = "v8"


class AzulArch(StrEnum):
    Arm = "arm"
    X86 = "x86"
    Mips = "mips"
    Ppc = "ppc"
    Sparcv9 = "sparcv9"
    Sparc = "sparc"


class AzulHwBitness(IntEnum):
    X32 = 32
    X64 = 64


class AzulAbi(StrEnum):
    HardFloat = "hard_float"
    SoftFloat = "soft_float"
    Spe = "spe"
    Any = "any"


class AzulArchiveType(StrEnum):
    Deb = "deb"
    Rpm = "rpm"
    Dmg = "dmg"
    Targz = "tar.gz"
    Zip = "zip"
    Cab = "cab"
    Msi = "msi"


class AzulReleaseStatus(StrEnum):
    Eval = "eval"
    Ea = "ea"
    Ga = "ga"
    Both = "both"


class AzulSupportTerm(StrEnum):
    Sts = "sts"
    Mts = "mts"
    Lts = "lts"


class AzulCertifications(StrEnum):
    Tck = "tck"
    _Aqavit = "aqavit"
    none = "none"


class AzulSignatureType(StrEnum):
    Openpgp = "openpgp"


class AzulOsQueryParam(StrEnum):
    Macos = "macos"
    Windows = "windows"
    Linux = "linux"
    LinuxMusl = "linux-musl"
    LinuxGlibc = "linux-glibc"
    Qnx = "qnx"
    Solaris = "solaris"


class AzulArchQueryParam(StrEnum):
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
    availability_types: list[AzulAvailabilityType] = []
    certifications: list[AzulCertifications] = []
    include_fields: list[str] = []
    page: int = 0
    page_size: int = 100


def azulApiPackagesUrl(query: AzulApiPackagesQuery = AzulApiPackagesQuery()):
    url = urlparse(AZUL_API_PACKAGES)
    return urlunparse(url._replace(query=query.to_query()))


def azulApiPackageDetailUrl(package_uuid: str):
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


class ZuluPackage(MetaBase):
    package_uuid: str
    name: Optional[str]
    java_version: list[int]
    openjdk_build_number: Optional[int]
    latest: Optional[bool]
    download_url: str
    product: Optional[AzulProduct]
    distro_version: list[int]
    availability_type: Optional[AzulAvailabilityType]


class ZuluPackageList(MetaBase):
    __root__: list[ZuluPackage]

    def __iter__(self) -> Generator[tuple[str, ZuluPackage], None, None]:
        yield from ((str(i), val) for i, val in enumerate(self.__root__))

    def __getitem__(self, item: int) -> ZuluPackage:
        return self.__root__[item]

    def append(self, pkg: ZuluPackage):
        self.__root__.append(pkg)


class ZuluPackagesDetail(MetaBase):
    __root__: list[ZuluPackageDetail]

    def __iter__(self) -> Generator[tuple[str, ZuluPackageDetail], None, None]:
        yield from ((str(i), val) for i, val in enumerate(self.__root__))

    def __getitem__(self, item: int) -> ZuluPackageDetail:
        return self.__root__[item]

    def append(self, pkg: ZuluPackageDetail):
        self.__root__.append(pkg)


MOJANG_OS_NAMES = ["mac-os", "linux", "windows"]

MOJANG_OS_ARCHITECTURES = [
    "x64",
    "x86",
    "arm64",
    "arm32",
]
