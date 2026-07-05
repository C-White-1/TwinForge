from dataclasses import dataclass


@dataclass(frozen=True)
class Revision:
    major: int
    minor: int

    def __str__(self):
        return f"{self.major}.{self.minor}"
