"""Versioning technique inspired by warehouse https://github.com/pypa/warehouse/blob/master/warehouse/__about__.py"""

__all__ = [
    "__version__",
    "__title__",
    "__author__",
    "__license__",
    "__copyright__",
]

# version criteria
# A.B.C
# A: Uncompatible change.
# B: Major change, but compatibility ensured somehow
# C: Minor change; no change in any interface
__version__ = '0.0.1'
__title__ = 'birdman'
__author__ = 'jinulee-v'
__license__ = 'GPL v3'
__copyright__ = 'Copyright 2021 jinulee-v'
