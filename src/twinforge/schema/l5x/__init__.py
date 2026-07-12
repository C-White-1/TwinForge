"""
Rockwell Studio 5000 L5X specification.
"""

from .controller import (
    CONTROLLER_ATTRIBUTES,
    CONTROLLER_ELEMENTS,
    REDUNDANCY_INFO_ATTRIBUTES,
    SAFETY_INFO_ATTRIBUTES,
    SECURITY_ATTRIBUTES,
)
from .reference import ReferenceType
from .spec import AttributeSpec, ElementSpec

__all__ = [
    "AttributeSpec",
    "ElementSpec",
    "CONTROLLER_ATTRIBUTES",
    "CONTROLLER_ELEMENTS",
    "REDUNDANCY_INFO_ATTRIBUTES",
    "ReferenceType",
    "SECURITY_ATTRIBUTES",
    "SAFETY_INFO_ATTRIBUTES",
]
