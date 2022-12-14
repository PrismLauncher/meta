import copy
import hashlib
import os
from collections import defaultdict, namedtuple
from operator import attrgetter
from pprint import pprint
from packaging import version as pversion
from typing import Optional, List

from meta.common import ensure_component_dir, launcher_path, upstream_path, static_path
from meta.common.mojang import VERSION_MANIFEST_FILE, MINECRAFT_COMPONENT, LWJGL3_COMPONENT, LWJGL_COMPONENT, \
    STATIC_OVERRIDES_FILE, VERSIONS_DIR, LIBRARY_PATCHES_FILE
from meta.model import MetaVersion, Library, GradleSpecifier, MojangLibraryDownloads, MojangArtifact, Dependency, \
    MetaPackage, MojangRules
from meta.model.mojang import MojangIndexWrap, MojangIndex, MojangVersion, LegacyOverrideIndex, LibraryPatches

APPLY_SPLIT_NATIVES_WORKAROUND = True

LAUNCHER_DIR = launcher_path()
UPSTREAM_DIR = upstream_path()
STATIC_DIR = static_path()

ensure_component_dir(MINECRAFT_COMPONENT)
ensure_component_dir(LWJGL_COMPONENT)
ensure_component_dir(LWJGL3_COMPONENT)


def map_log4j_artifact(version):
    x = pversion.parse(version)
    if x <= pversion.parse("2.0"):
        return "2.0-beta9-fixed", "https://files.prismlauncher.org/maven/%s"
    if x <= pversion.parse("2.17.1"):
        return "2.17.1", "https://repo1.maven.org/maven2/%s"  # This is the only version that's patched (as of 2022/02/19)
    return None, None


LOG4J_HASHES = {
    "2.0-beta9-fixed": {
        "log4j-api": {
            "sha1": "b61eaf2e64d8b0277e188262a8b771bbfa1502b3",
            "size": 107347
        },
        "log4j-core": {
            "sha1": "677991ea2d7426f76309a73739cecf609679492c",
            "size": 677588
        }
    },
    "2.17.1": {
        "log4j-api": {
            "sha1": "d771af8e336e372fb5399c99edabe0919aeaf5b2",
            "size": 301872
        },
        "log4j-core": {
            "sha1": "779f60f3844dadc3ef597976fcb1e5127b1f343d",
            "size": 1790452
        },
        "log4j-slf4j18-impl": {
            "sha1": "ca499d751f4ddd8afb016ef698c30be0da1d09f7",
            "size": 21268
        }
    }
}

# We want versions that contain natives for all platforms. If there are multiple, pick the latest one
# LWJGL versions we want
PASS_VARIANTS = [
    # "beed62ec1d40ae89d808fe70b83df6bd4b3be81f",  # 3.3.1 (2022-05-18 13:51:54+00:00) split natives, without workaround
    "8836c419f90f69a278b97d945a34af165c24ff60",  # 3.3.1 (2022-05-18 13:51:54+00:00) split natives, with workaround
    "ea4973ebc9eadf059f30f0958c89f330898bff51",  # 3.2.2 (2019-07-04 14:41:05+00:00) will be patched, missing tinyfd
    "8e1f89b96c6f583a0e494949c75115ed13412ba1",  # 3.2.1 (2019-02-13 16:12:08+00:00)
    "7ed2372097dbd635f5aef3137711141ce91c4ee9",  # 3.1.6 (2018-11-29 13:11:38+00:00)
    "5a006b7c72a080ac673fff02b259f3127c376655",  # 3.1.2 (2018-06-21 12:57:11+00:00)
    "a3f254df5a63a0a1635755733022029e8cfae1b3",  # 2.9.4-nightly-20150209 (2016-12-20 14:05:34+00:00)
    "879be09c0bd0d4bafc2ea4ea3d2ab8607a0d976c",  # 2.9.3 (2015-01-30 11:58:24+00:00)
    "8d4951d00253dfaa36a0faf1c8be541431861c30",  # 2.9.1 (2014-05-22 14:44:33+00:00)
    "cf58c9f92fed06cb041a7244c6b4b667e6d544cc",  # 2.9.1-nightly-20131120 (2013-12-06 13:55:34+00:00)
    "27dcadcba29a1a7127880ca1a77efa9ece866f24",  # 2.9.0 (2013-09-06 12:31:58+00:00)
]

# LWJGL versions we def. don't want!
BAD_VARIANTS = [
    "e1106ca765798218323b7a6d7528050260ea9d88",  # 3.3.1 (2022-05-04 14:41:35+00:00) doesn't use split natives
    "90b3d9ca01058286c033b6b7ae7f6dc370a04015",  # 3.2.2 (2022-03-31 14:53:25+00:00) only linux, windows
    "d986df9598fa2bcf4a5baab5edf044548e66d011",  # 3.2.2 (2021-12-10 03:36:38+00:00) only linux, windows
    "4b73fccb9e5264c2068bdbc26f9651429abbf21a",  # 3.2.2 (2021-08-25 14:41:57+00:00) only linux, windows
    "090cec3577ecfe438b890b2a9410ea07aa725e16",  # 3.2.2 (2021-04-07 14:04:09+00:00) only linux, windows
    "ab463e9ebc6a36abf22f2aa27b219dd372ff5069",  # 3.2.2 (2019-07-19 09:25:47+00:00) only linux, windows
    "8bde129ef334023c365bd7f57512a4bf5e72a378",  # 3.2.1 (2019-04-18 11:05:19+00:00) only osx, windows
    "65b2ce1f2b869bf98b8dd7ec0bc6956967d04811",  # 3.1.6 (2019-04-18 11:05:19+00:00) only linux
    "f04052162b50fa1433f67e1a90bc79466c4ab776",  # 2.9.0 (2013-10-21 16:34:47+00:00) only linux, windows
    "6442fc475f501fbd0fc4244fd1c38c02d9ebaf7e",  # 2.9.0 (2011-03-30 22:00:00+00:00) fine but newer variant available
]


def add_or_get_bucket(buckets, rules: Optional[MojangRules]) -> MetaVersion:
    rule_hash = None
    if rules:
        rule_hash = hash(rules.json())

    if rule_hash in buckets:
        bucket = buckets[rule_hash]
    else:
        bucket = MetaVersion(name="LWJGL", version="undetermined", uid=LWJGL_COMPONENT)
        bucket.type = "release"
        buckets[rule_hash] = bucket
    return bucket


def hash_lwjgl_version(lwjgl: MetaVersion):
    lwjgl_copy = copy.deepcopy(lwjgl)
    lwjgl_copy.release_time = None
    return hashlib.sha1(lwjgl_copy.json().encode("utf-8", "strict")).hexdigest()


def sort_libs_by_name(library):
    return library.name


LWJGLEntry = namedtuple('LWJGLEntry', ('version', 'sha1'))

lwjglVersionVariants = defaultdict(list)


def add_lwjgl_version(variants, lwjgl):
    lwjgl_copy = copy.deepcopy(lwjgl)
    libraries = list(lwjgl_copy.libraries)
    libraries.sort(key=sort_libs_by_name)
    lwjgl_copy.libraries = libraries

    version = lwjgl_copy.version
    current_hash = hash_lwjgl_version(lwjgl_copy)
    found = False
    for variant in variants[version]:
        existing_hash = variant.sha1
        if current_hash == existing_hash:
            found = True
            break
    if not found:
        print("!!! New variant for LWJGL version %s" % version)
        variants[version].append(LWJGLEntry(version=lwjgl_copy, sha1=current_hash))


def remove_paths_from_lib(lib):
    if lib.downloads.artifact:
        lib.downloads.artifact.path = None
    if lib.downloads.classifiers:
        for key, value in lib.downloads.classifiers.items():
            value.path = None


def adapt_new_style_arguments(arguments):
    foo = []
    # we ignore the jvm arguments entirely.
    # grab the strings, log the complex stuff
    for arg in arguments.game:
        if isinstance(arg, str):
            if arg == '--clientId':
                continue
            if arg == '${clientid}':
                continue
            if arg == '--xuid':
                continue
            if arg == '${auth_xuid}':
                continue
            foo.append(arg)
        else:
            print("!!! Unrecognized structure in Minecraft game arguments:")
            pprint(arg)
    return ' '.join(foo)


def is_macos_only(rules: Optional[MojangRules]):
    allows_osx = False
    allows_all = False
    # print("Considering", specifier, "rules", rules)
    if rules:
        for rule in rules:
            if rule.action == "allow" and rule.os and rule.os.name == "osx":
                allows_osx = True
            if rule.action == "allow" and not rule.os:
                allows_all = True
        if allows_osx and not allows_all:
            return True
    return False


def patch_library(lib: Library, patches: LibraryPatches) -> List[Library]:
    to_patch = [lib]

    new_libraries = []
    while to_patch:
        target = to_patch.pop(0)

        for patch in patches:
            if patch.applies(target):
                if patch.override:
                    target.merge(patch.override)

                if patch.additionalLibraries:
                    additional_copy = copy.deepcopy(patch.additionalLibraries)
                    new_libraries += list(dict.fromkeys(additional_copy))
                    if patch.patchAdditionalLibraries:
                        to_patch += additional_copy

    return new_libraries


def process_single_variant(lwjgl_variant: MetaVersion, patches: LibraryPatches):
    lwjgl_version = lwjgl_variant.version
    v = copy.deepcopy(lwjgl_variant)

    new_libraries = []
    for lib in v.libraries:
        new_libraries += patch_library(lib, patches)
    v.libraries += list(dict.fromkeys(new_libraries))

    if lwjgl_version[0] == '2':
        filename = os.path.join(LAUNCHER_DIR, LWJGL_COMPONENT, f"{lwjgl_version}.json")

        v.name = 'LWJGL 2'
        v.uid = LWJGL_COMPONENT
        v.conflicts = [Dependency(uid=LWJGL3_COMPONENT)]
    elif lwjgl_version[0] == '3':
        filename = os.path.join(LAUNCHER_DIR, LWJGL3_COMPONENT, f"{lwjgl_version}.json")

        v.name = 'LWJGL 3'
        v.uid = LWJGL3_COMPONENT
        v.conflicts = [Dependency(uid=LWJGL_COMPONENT)]
        # remove jutils and jinput from LWJGL 3
        # this is a dependency that Mojang kept in, but doesn't belong there anymore
        filtered_libraries = list(filter(lambda l: l.name.artifact not in ["jutils", "jinput"], v.libraries))
        v.libraries = filtered_libraries
    else:
        raise Exception("LWJGL version not recognized: %s" % v.version)

    v.volatile = True
    v.order = -1
    good = True
    for lib in v.libraries:
        # skip libraries without natives or that we patched
        if not lib.natives or lib in new_libraries:
            continue
        checked_dict = {'linux', 'windows', 'osx'}
        if not checked_dict.issubset(lib.natives.keys()):
            print("Missing system classifier!", v.version, lib.name, lib.natives.keys())
            good = False
            break
        if lib.downloads:
            for entry in checked_dict:
                baked_entry = lib.natives[entry]
                if baked_entry not in lib.downloads.classifiers:
                    print("Missing download for classifier!", v.version, lib.name, baked_entry,
                          lib.downloads.classifiers.keys())
                    good = False
                    break
    if good:
        v.write(filename)
    else:
        print("Skipped LWJGL", v.version)


def lib_is_split_native(lib: Library) -> bool:
    if lib.name.classifier and lib.name.classifier.startswith("natives-"):
        return True
    return False


def version_has_split_natives(v: MojangVersion) -> bool:
    for lib in v.libraries:
        if lib_is_split_native(lib):
            return True
    return False


def main():
    # get the local version list
    override_index = LegacyOverrideIndex.parse_file(os.path.join(STATIC_DIR, STATIC_OVERRIDES_FILE))
    library_patches = LibraryPatches.parse_file(os.path.join(STATIC_DIR, LIBRARY_PATCHES_FILE))

    found_any_lwjgl3 = False

    for filename in os.listdir(os.path.join(UPSTREAM_DIR, VERSIONS_DIR)):
        input_file = os.path.join(UPSTREAM_DIR, VERSIONS_DIR, filename)
        if not input_file.endswith(".json"):
            # skip non JSON files
            continue
        print("Processing", filename)
        mojang_version = MojangVersion.parse_file(input_file)
        v = mojang_version.to_meta_version("Minecraft", MINECRAFT_COMPONENT, mojang_version.id)

        libs_minecraft = []
        new_libs_minecraft = []
        is_lwjgl_3 = False
        has_split_natives = version_has_split_natives(v)
        buckets = {}

        for lib in v.libraries:
            specifier = lib.name

            # generic fixes
            remove_paths_from_lib(lib)

            if APPLY_SPLIT_NATIVES_WORKAROUND and lib_is_split_native(lib):
                # merge classifier into artifact name to workaround bug in launcher
                specifier.artifact += f"-{specifier.classifier}"
                specifier.classifier = None

            if specifier.is_lwjgl():
                if has_split_natives:  # implies lwjgl3
                    bucket = add_or_get_bucket(buckets, None)
                    is_lwjgl_3 = True
                    found_any_lwjgl3 = True
                    bucket.version = specifier.version
                    if not bucket.libraries:
                        bucket.libraries = []
                    bucket.libraries.append(lib)
                    bucket.release_time = v.release_time
                else:
                    rules = None
                    if lib.rules:
                        rules = lib.rules
                        lib.rules = None
                    if is_macos_only(rules):
                        print("Candidate library ", specifier, " is only for macOS and is therefore ignored.")
                        continue
                    bucket = add_or_get_bucket(buckets, rules)
                    if specifier.group == "org.lwjgl.lwjgl" and specifier.artifact == "lwjgl":
                        bucket.version = specifier.version
                    if specifier.group == "org.lwjgl" and specifier.artifact == "lwjgl":
                        is_lwjgl_3 = True
                        found_any_lwjgl3 = True
                        bucket.version = specifier.version
                    if not bucket.libraries:
                        bucket.libraries = []
                    bucket.libraries.append(lib)
                    bucket.release_time = v.release_time
            # FIXME: workaround for insane log4j nonsense from December 2021. Probably needs adjustment.
            elif lib.name.is_log4j():
                version_override, maven_override = map_log4j_artifact(lib.name.version)

                if version_override and maven_override:
                    if version_override not in LOG4J_HASHES:
                        raise Exception("ERROR: unhandled log4j version (overriden) %s!" % version_override)

                    if lib.name.artifact not in LOG4J_HASHES[version_override]:
                        raise Exception("ERROR: unhandled log4j artifact %s!" % lib.name.artifact)

                    replacement_name = GradleSpecifier("org.apache.logging.log4j", lib.name.artifact, version_override)
                    artifact = MojangArtifact(
                        url=maven_override % (replacement_name.path()),
                        sha1=LOG4J_HASHES[version_override][lib.name.artifact]["sha1"],
                        size=LOG4J_HASHES[version_override][lib.name.artifact]["size"]
                    )

                    libs_minecraft.append(Library(
                        name=replacement_name,
                        downloads=MojangLibraryDownloads(artifact=artifact)
                    ))
                else:
                    libs_minecraft.append(lib)
            else:
                new_libs_minecraft += patch_library(lib, library_patches)
                libs_minecraft.append(lib)
        if len(buckets) == 1:
            for key in buckets:
                lwjgl = buckets[key]
                lwjgl.libraries = sorted(lwjgl.libraries, key=attrgetter("name"))
                add_lwjgl_version(lwjglVersionVariants, lwjgl)
                print("Found only candidate LWJGL", lwjgl.version, key)
        else:
            # multiple buckets for LWJGL. [None] is common to all, other keys are for different sets of rules
            for key in buckets:
                if key is None:
                    continue
                lwjgl = buckets[key]
                if None in buckets:
                    lwjgl.libraries = sorted(lwjgl.libraries + buckets[None].libraries, key=attrgetter("name"))
                else:
                    lwjgl.libraries = sorted(lwjgl.libraries, key=attrgetter('name'))
                add_lwjgl_version(lwjglVersionVariants, lwjgl)
                print("Found candidate LWJGL", lwjgl.version, key)
            # remove the common bucket...
            if None in buckets:
                del buckets[None]
        v.libraries = libs_minecraft + list(dict.fromkeys(new_libs_minecraft))

        if is_lwjgl_3:
            lwjgl_dependency = Dependency(uid=LWJGL3_COMPONENT)
        else:
            lwjgl_dependency = Dependency(uid=LWJGL_COMPONENT)
        if len(buckets) == 1:
            suggested_version = next(iter(buckets.values())).version
            if is_lwjgl_3:
                lwjgl_dependency.suggests = suggested_version
            else:
                lwjgl_dependency.suggests = '2.9.4-nightly-20150209'
        else:
            bad_versions = {'3.1.6', '3.2.1'}
            our_versions = set()

            for lwjgl in iter(buckets.values()):
                our_versions = our_versions.union({lwjgl.version})

            if our_versions == bad_versions:
                print("Found broken 3.1.6/3.2.1 combo, forcing LWJGL to 3.2.1")
                suggested_version = '3.2.1'
                lwjgl_dependency.suggests = suggested_version
            else:
                raise Exception("ERROR: cannot determine single suggested LWJGL version in %s" % mojang_version.id)

        # if it uses LWJGL 3, add the trait that enables starting on first thread on macOS
        if is_lwjgl_3:
            if not v.additional_traits:
                v.additional_traits = []
            v.additional_traits.append("FirstThreadOnMacOS")
        v.requires = [lwjgl_dependency]
        v.order = -2
        # process 1.13 arguments into previous version
        if not mojang_version.minecraft_arguments and mojang_version.arguments:
            v.minecraft_arguments = adapt_new_style_arguments(mojang_version.arguments)
        out_filename = os.path.join(LAUNCHER_DIR, MINECRAFT_COMPONENT, f"{v.version}.json")
        if v.version in override_index.versions:
            override = override_index.versions[v.version]
            override.apply_onto_meta_version(v)
        v.write(out_filename)

    for lwjglVersionVariant in lwjglVersionVariants:
        decided_variant = None
        passed_variants = 0
        unknown_variants = 0
        print("%d variant(s) for LWJGL %s:" % (len(lwjglVersionVariants[lwjglVersionVariant]), lwjglVersionVariant))

        for variant in lwjglVersionVariants[lwjglVersionVariant]:
            if variant.sha1 in BAD_VARIANTS:
                print("Variant %s ignored because it's marked as bad." % variant.sha1)
                continue
            if variant.sha1 in PASS_VARIANTS:
                print("Variant %s accepted." % variant.sha1)
                decided_variant = variant
                passed_variants += 1
                continue
            # print natives classifiers to decide which variant to use
            n = [x.natives.keys() for x in variant.version.libraries if x.natives is not None]
            print(n)

            print(f"    \"{variant.sha1}\",  # {lwjglVersionVariant} ({variant.version.release_time})")
            unknown_variants += 1
        print("")

        if decided_variant and passed_variants == 1 and unknown_variants == 0:
            process_single_variant(decided_variant.version, library_patches)
        else:
            raise Exception("No variant decided for version %s out of %d possible ones and %d unknown ones." % (
                lwjglVersionVariant, passed_variants, unknown_variants))

    lwjgl_package = MetaPackage(uid=LWJGL_COMPONENT, name='LWJGL 2')
    lwjgl_package.write(os.path.join(LAUNCHER_DIR, LWJGL_COMPONENT, "package.json"))

    if found_any_lwjgl3:
        lwjgl_package = MetaPackage(uid=LWJGL3_COMPONENT, name='LWJGL 3')
        lwjgl_package.write(os.path.join(LAUNCHER_DIR, LWJGL3_COMPONENT, "package.json"))

    mojang_index = MojangIndexWrap(MojangIndex.parse_file(os.path.join(UPSTREAM_DIR, VERSION_MANIFEST_FILE)))

    minecraft_package = MetaPackage(uid=MINECRAFT_COMPONENT, name='Minecraft')
    minecraft_package.recommended = [mojang_index.latest.release]
    minecraft_package.write(os.path.join(LAUNCHER_DIR, MINECRAFT_COMPONENT, "package.json"))


if __name__ == '__main__':
    main()
