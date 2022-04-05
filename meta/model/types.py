from typing import Optional


class GradleSpecifier:
    """
        A gradle specifier - a maven coordinate. Like one of these:
        "org.lwjgl.lwjgl:lwjgl:2.9.0"
        "net.java.jinput:jinput:2.0.5"
        "net.minecraft:launchwrapper:1.5"
    """

    def __init__(self, group: str, artifact: str, version: str, classifier: Optional[str] = None,
                 extension: Optional[str] = None):
        if extension is None:
            extension = "jar"
        self.group = group
        self.artifact = artifact
        self.version = version
        self.classifier = classifier
        self.extension = extension

    def __str__(self):
        ext = ''
        if self.extension != 'jar':
            ext = "@%s" % self.extension
        if self.classifier:
            return "%s:%s:%s:%s%s" % (self.group, self.artifact, self.version, self.classifier, ext)
        else:
            return "%s:%s:%s%s" % (self.group, self.artifact, self.version, ext)

    def filename(self):
        if self.classifier:
            return "%s-%s-%s.%s" % (self.artifact, self.version, self.classifier, self.extension)
        else:
            return "%s-%s.%s" % (self.artifact, self.version, self.extension)

    def base(self):
        return "%s/%s/%s/" % (self.group.replace('.', '/'), self.artifact, self.version)

    def path(self):
        return self.base() + self.filename()

    def __repr__(self):
        return f"GradleSpecifier('{self}')"

    def is_lwjgl(self):
        return self.group in ("org.lwjgl", "org.lwjgl.lwjgl", "net.java.jinput", "net.java.jutils")

    def is_log4j(self):
        return self.group == "org.apache.logging.log4j"

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other):
        return str(self) < str(other)

    def __gt__(self, other):
        return str(self) > str(other)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def from_string(cls, v: str):
        ext_split = v.split('@')

        components = ext_split[0].split(':')
        group = components[0]
        artifact = components[1]
        version = components[2]

        extension = None
        if len(ext_split) == 2:
            extension = ext_split[1]

        classifier = None
        if len(components) == 4:
            classifier = components[3]
        return cls(group, artifact, version, classifier, extension)

    @classmethod
    def validate(cls, v):
        if isinstance(v, cls):
            return v
        if isinstance(v, str):
            return cls.from_string(v)
        raise TypeError("Invalid type")
