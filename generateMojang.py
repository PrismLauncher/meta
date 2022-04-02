import copy
import hashlib
import os
from collections import defaultdict, namedtuple
from operator import attrgetter
from pprint import pprint
from typing import Optional

from meta.common import ensure_component_dir, polymc_path, upstream_path
from meta.common.mojang import VERSION_MANIFEST_FILE, MINECRAFT_COMPONENT, LWJGL3_COMPONENT, LWJGL_COMPONENT, \
    STATIC_OVERRIDES_FILE, VERSIONS_DIR
from meta.model import MetaVersionFile, Library, GradleSpecifier, MojangLibraryDownloads, MojangArtifact, Dependency, \
    MetaPackageData, MojangRules
from meta.model.mojang import MojangIndexWrap, MojangIndex, MojangVersionFile, LegacyOverrideIndex
from updateMojang import STATIC_DIR

PMC_DIR = polymc_path()
UPSTREAM_DIR = upstream_path()

ensure_component_dir(MINECRAFT_COMPONENT)
ensure_component_dir(LWJGL_COMPONENT)
ensure_component_dir(LWJGL3_COMPONENT)


def map_log4j_artifact(version):
    if version == "2.0-beta9":
        return "2.0-beta9-fixed", "https://polymc.github.io/files/maven/%s"
    return "2.17.1", "https://repo1.maven.org/maven2/%s"  # This is the only version that's patched (as of 2022/02/19)


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

# LWJGL versions we want
PASS_VARIANTS = [
    "d986df9598fa2bcf4a5baab5edf044548e66d011",  # 3.2.2 (2021-12-10 03:36:38+00:00)
    "5a006b7c72a080ac673fff02b259f3127c376655",  # 3.1.2 (2018-06-21 12:57:11+00:00)
    "f04052162b50fa1433f67e1a90bc79466c4ab776",  # 2.9.0 (2013-10-21 16:34:47+00:00)
    "a3f254df5a63a0a1635755733022029e8cfae1b3",  # 2.9.4-nightly-20150209 (2016-12-20 14:05:34+00:00)
    "65b2ce1f2b869bf98b8dd7ec0bc6956967d04811",  # 3.1.6 (2019-04-18 11:05:19+00:00)
    "8bde129ef334023c365bd7f57512a4bf5e72a378",  # 3.2.1 (2019-04-18 11:05:19+00:00)
    "8d4951d00253dfaa36a0faf1c8be541431861c30",  # 2.9.1 (2014-05-22 14:44:33+00:00)
    "cf58c9f92fed06cb041a7244c6b4b667e6d544cc",  # 2.9.1-nightly-20131120 (2013-12-06 13:55:34+00:00)
    "879be09c0bd0d4bafc2ea4ea3d2ab8607a0d976c",  # 2.9.3 (2015-01-30 11:58:24+00:00)
]

# LWJGL versions we def. don't want!
BAD_VARIANTS = [
    "4b73fccb9e5264c2068bdbc26f9651429abbf21a",  # 3.2.2 (2021-08-25 14:41:57+00:00)
    "ab463e9ebc6a36abf22f2aa27b219dd372ff5069",  # 3.2.2 (2019-07-19 09:25:47+00:00)
    "ea4973ebc9eadf059f30f0958c89f330898bff51",  # 3.2.2 (2019-07-04 14:41:05+00:00)
    "27dcadcba29a1a7127880ca1a77efa9ece866f24",  # 2.9.0 (2013-09-06 12:31:58+00:00)
    "6442fc475f501fbd0fc4244fd1c38c02d9ebaf7e",  # 2.9.0 (2011-03-30 22:00:00+00:00)
    "7ed2372097dbd635f5aef3137711141ce91c4ee9",  # 3.1.6 (2018-11-29 13:11:38+00:00)
    "8e1f89b96c6f583a0e494949c75115ed13412ba1",  # 3.2.1 (2019-02-13 16:12:08+00:00)
]


def add_or_get_bucket(buckets, rules: Optional[MojangRules]) -> MetaVersionFile:
    rule_hash = None
    if rules:
        rule_hash = hash(rules.json())

    if rule_hash in buckets:
        bucket = buckets[rule_hash]
    else:
        bucket = MetaVersionFile(name="LWJGL", version="undetermined", uid=LWJGL_COMPONENT)
        bucket.type = "release"
        buckets[rule_hash] = bucket
    return bucket


def hash_lwjgl_version(lwjgl: MetaVersionFile):
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
        existingHash = variant.sha1
        if current_hash == existingHash:
            found = True
            break
    if not found:
        print("!!! New variant for LWJGL version %s" % (version))
        variants[version].append(LWJGLEntry(version=lwjgl_copy, sha1=current_hash))


def removePathsFromLib(lib):
    if lib.downloads.artifact:
        lib.downloads.artifact.path = None
    if lib.downloads.classifiers:
        for key, value in lib.downloads.classifiers.items():
            value.path = None


def adaptNewStyleArguments(arguments):
    outarr = []
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
            outarr.append(arg)
        else:
            print("!!! Unrecognized structure in Minecraft game arguments:")
            pprint(arg)
    return ' '.join(outarr)


def is_macos_only(rules: Optional[MojangRules], specifier):
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


def process_single_variant(lwjgl_variant: MetaVersionFile):
    lwjglVersion = lwjgl_variant.version
    versionObj = copy.deepcopy(lwjgl_variant)
    if lwjglVersion[0] == '2':
        filename = os.path.join(PMC_DIR, LWJGL_COMPONENT, f"{lwjglVersion}.json")
        versionObj.name = 'LWJGL 2'
        versionObj.uid = LWJGL_COMPONENT
        versionObj.conflicts = [Dependency(uid=LWJGL3_COMPONENT)]
    elif lwjglVersion[0] == '3':
        filename = os.path.join(PMC_DIR, LWJGL3_COMPONENT, f"{lwjglVersion}.json")
        versionObj.name = 'LWJGL 3'
        versionObj.uid = LWJGL3_COMPONENT
        versionObj.conflicts = [Dependency(uid=LWJGL_COMPONENT)]
        # remove jutils and jinput from LWJGL 3
        # this is a dependency that Mojang kept in, but doesn't belong there anymore
        filteredLibraries = list(
            filter(lambda lib: not lib.name.artifact in ["jutils", "jinput"], versionObj.libraries))
        versionObj.libraries = filteredLibraries
    else:
        raise Exception("LWJGL version not recognized: %s" % versionObj.version)

    versionObj.volatile = True
    versionObj.order = -1
    good = True
    for lib in versionObj.libraries:
        if not lib.natives:
            continue
        checkedDict = {'linux', 'windows', 'osx'}
        if not checkedDict.issubset(lib.natives.keys()):
            print("Missing system classifier!", versionObj.version, lib.name, lib.natives.keys())
            good = False
            break
        if lib.downloads:
            for entry in checkedDict:
                bakedEntry = lib.natives[entry]
                if not bakedEntry in lib.downloads.classifiers:
                    print("Missing download for classifier!", versionObj.version, lib.name, bakedEntry,
                          lib.downloads.classifiers.keys())
                    good = False
                    break
    if good:
        versionObj.write(filename)
    else:
        print("Skipped LWJGL", versionObj.version)


def main():
    # get the local version list
    override_index = LegacyOverrideIndex.parse_file(os.path.join(STATIC_DIR, STATIC_OVERRIDES_FILE))

    found_any_lwjgl3 = False

    for filename in os.listdir(os.path.join(UPSTREAM_DIR, VERSIONS_DIR)):
        input_file = os.path.join(UPSTREAM_DIR, VERSIONS_DIR, filename)
        if not input_file.endswith(".json"):
            # skip non JSON files
            continue
        print("Processing", filename)
        mojangVersionFile = MojangVersionFile.parse_file(input_file)
        versionFile = mojangVersionFile.to_meta_version("Minecraft", MINECRAFT_COMPONENT, mojangVersionFile.id)
        libs_minecraft = []
        is_lwjgl_3 = False
        buckets = {}
        for pmcLib in versionFile.libraries:
            removePathsFromLib(pmcLib)
            specifier = pmcLib.name
            ruleHash = None
            if specifier.is_lwjgl():
                rules = None
                if pmcLib.rules:
                    rules = pmcLib.rules
                    pmcLib.rules = None
                if is_macos_only(rules, specifier):
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
                bucket.libraries.append(pmcLib)
                bucket.release_time = versionFile.release_time
            else:
                # FIXME: workaround for insane log4j nonsense from December 2021. Probably needs adjustment.
                if pmcLib.name.is_log4j():
                    versionOverride, mavenOverride = map_log4j_artifact(pmcLib.name.version)

                    if versionOverride not in LOG4J_HASHES:
                        raise Exception("ERROR: unhandled log4j version (overriden) %s!" % versionOverride)

                    if pmcLib.name.artifact not in LOG4J_HASHES[versionOverride]:
                        raise Exception("ERROR: unhandled log4j artifact %s!" % pmcLib.name.artifact)

                    replacement_name = GradleSpecifier(
                        "org.apache.logging.log4j:%s:%s" % (pmcLib.name.artifact, versionOverride))
                    artifact = MojangArtifact(
                        url=mavenOverride % (replacement_name.path()),
                        sha1=LOG4J_HASHES[versionOverride][pmcLib.name.artifact]["sha1"],
                        size=LOG4J_HASHES[versionOverride][pmcLib.name.artifact]["size"]
                    )

                    replacementLib = Library(
                        name=replacement_name,
                        downloads=MojangLibraryDownloads(artifact=artifact)
                    )
                    libs_minecraft.append(replacementLib)
                else:
                    libs_minecraft.append(pmcLib)
        if len(buckets) == 1:
            for key in buckets:
                keyBucket = buckets[key]
                keyBucket.libraries = sorted(keyBucket.libraries, key=attrgetter("name"))
                add_lwjgl_version(lwjglVersionVariants, keyBucket)
                print("Found only candidate LWJGL", keyBucket.version, key)
        else:
            # multiple buckets for LWJGL. [None] is common to all, other keys are for different sets of rules
            for key in buckets:
                if key is None:
                    continue
                keyBucket = buckets[key]
                if None in buckets:
                    keyBucket.libraries = sorted(keyBucket.libraries + buckets[None].libraries, key=attrgetter("name"))
                else:
                    keyBucket.libraries = sorted(keyBucket.libraries, key=attrgetter('name'))
                add_lwjgl_version(lwjglVersionVariants, keyBucket)
                print("Found candidate LWJGL", keyBucket.version, key)
            # remove the common bucket...
            if None in buckets:
                del buckets[None]
        versionFile.libraries = libs_minecraft
        depentry = None

        if is_lwjgl_3:
            depentry = Dependency(uid=LWJGL3_COMPONENT)
        else:
            depentry = Dependency(uid=LWJGL_COMPONENT)
        if len(buckets) == 1:
            suggestedVersion = next(iter(buckets.values())).version
            # HACK: forcing hard dependencies here for now...
            # the UI doesn't know how to filter by this and it looks odd, but it works
            if is_lwjgl_3:
                depentry.suggests = suggestedVersion
                depentry.equals = suggestedVersion
            else:
                depentry.suggests = '2.9.4-nightly-20150209'
        else:
            badVersions1 = {'3.1.6', '3.2.1'}
            ourVersions = set()

            for lwjgl in iter(buckets.values()):
                ourVersions = ourVersions.union({lwjgl.version})

            if ourVersions == badVersions1:
                print("Found broken 3.1.6/3.2.1 combo, forcing LWJGL to 3.2.1")
                suggestedVersion = '3.2.1'
                depentry.suggests = suggestedVersion
            else:
                raise Exception("ERROR: cannot determine single suggested LWJGL version in %s" % mojangVersionFile.id)

        # if it uses LWJGL 3, add the trait that enables starting on first thread on macOS
        if is_lwjgl_3:
            if not versionFile.additional_traits:
                versionFile.additional_traits = []
            versionFile.additional_traits.append("FirstThreadOnMacOS")
        versionFile.requires = [depentry]
        versionFile.order = -2
        # process 1.13 arguments into previous version
        if not mojangVersionFile.minecraftArguments and mojangVersionFile.arguments:
            versionFile.minecraft_arguments = adaptNewStyleArguments(mojangVersionFile.arguments)
        out_filename = os.path.join(PMC_DIR, MINECRAFT_COMPONENT, f"{versionFile.version}.json")
        if versionFile.version in override_index.versions:
            override = override_index.versions[versionFile.version]
            override.apply_onto_meta_version(versionFile)
        versionFile.write(out_filename)

    for lwjglVersionVariant in lwjglVersionVariants:
        decidedVariant = None
        passedVariants = 0
        unknownVariants = 0
        print("%d variant(s) for LWJGL %s:" % (len(lwjglVersionVariants[lwjglVersionVariant]), lwjglVersionVariant))

        for variant in lwjglVersionVariants[lwjglVersionVariant]:
            if variant.sha1 in BAD_VARIANTS:
                print("Variant %s ignored because it's marked as bad." % (variant.sha1))
                continue
            if variant.sha1 in PASS_VARIANTS:
                print("Variant %s accepted." % (variant.sha1))
                decidedVariant = variant
                passedVariants += 1
                continue

            print(f"    \"{variant.sha1}\",  # {lwjglVersionVariant} ({variant.version.release_time})")
            unknownVariants += 1
        print("")

        if decidedVariant and passedVariants == 1 and unknownVariants == 0:
            process_single_variant(decidedVariant.version)
        else:
            raise Exception("No variant decided for version %s out of %d possible ones and %d unknown ones." % (
                lwjglVersionVariant, passedVariants, unknownVariants))

    lwjglSharedData = MetaPackageData(uid=LWJGL_COMPONENT, name='LWJGL 2')
    lwjglSharedData.recommended = ['2.9.4-nightly-20150209']
    lwjglSharedData.write(os.path.join(PMC_DIR, LWJGL_COMPONENT, "package.json"))

    if found_any_lwjgl3:
        lwjglSharedData = MetaPackageData(uid=LWJGL3_COMPONENT, name='LWJGL 3')
        lwjglSharedData.recommended = ['3.1.2']
        lwjglSharedData.write(os.path.join(PMC_DIR, LWJGL3_COMPONENT, "package.json"))

    localVersionlist = MojangIndexWrap(MojangIndex.parse_file(os.path.join(UPSTREAM_DIR, VERSION_MANIFEST_FILE)))

    mcSharedData = MetaPackageData(uid=MINECRAFT_COMPONENT, name='Minecraft')
    mcSharedData.recommended = [localVersionlist.latest.release]
    mcSharedData.write(os.path.join(PMC_DIR, MINECRAFT_COMPONENT, "package.json"))


if __name__ == '__main__':
    main()
