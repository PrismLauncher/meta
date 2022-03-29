class GradleSpecifier(str):
    """
        A gradle specifier - a maven coordinate. Like one of these:
        "org.lwjgl.lwjgl:lwjgl:2.9.0"
        "net.java.jinput:jinput:2.0.5"
        "net.minecraft:launchwrapper:1.5"
    """

    def __init__(self, name: str):
        ext_split = name.split('@')

        components = ext_split[0].split(':')
        self.group = components[0]
        self.artifact = components[1]
        self.version = components[2]

        self.extension = 'jar'
        if len(ext_split) == 2:
            self.extension = ext_split[1]

        self.classifier = None
        if len(components) == 4:
            self.classifier = components[3]

    def __new__(cls, name: str):
        return super(GradleSpecifier, cls).__new__(cls, name)

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