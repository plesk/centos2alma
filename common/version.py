# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.

class KernelVersion():
    """Linux kernel version representation class."""

    major: str
    minor: str
    patch: str
    build: str
    distro: str
    arch: str

    def _extract_with_build(self, version: str):
        main_part, secondary_part = version.split("-")

        self.major, self.minor, self.patch = main_part.split(".")

        for iter in range(len(secondary_part)):
            if secondary_part[iter].isalpha():
                self.build = secondary_part[:iter - 1]
                suffix = secondary_part[iter:]
                self.distro, self.arch = suffix.split(".")
                break

    def _extract_no_build(self, version: str):
        self.build = ""
        self.major, self.minor, self.patch, self.distro, self.arch = version.split(".")

    def __init__(self, version: str):
        """Initialize a KernelVersion object."""
        self.major = 0
        self.minor = 0
        self.patch = 0
        self.build = 0
        self.distro = ""
        self.arch = ""

        if "-" in version:
            self._extract_with_build(version)
        else:
            self._extract_no_build(version)

    def __str__(self):
        """Return a string representation of a KernelVersion object."""
        if self.build == "":
            return f"{self.major}.{self.minor}.{self.patch}.{self.distro}.{self.arch}"

        return f"{self.major}.{self.minor}.{self.patch}-{self.build}.{self.distro}.{self.arch}"

    def __lt__(self, other):
        return self.major < other.major or self.minor < other.minor or self.patch < other.patch or self.build < other.build

    def __eq__(self, other):
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch and self.build == other.build

    def __ge__(self, other):
        return not self.__lt__(other)
