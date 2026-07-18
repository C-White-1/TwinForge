"""
Rockwell Studio 5000 L5X specification.
"""

from .controller import (
    CONTROLLER_ATTRIBUTES,
    CONTROLLER_ELEMENTS,
    PRIMARY_ACTION_SET_ATTRIBUTES,
    REDUNDANCY_INFO_ATTRIBUTES,
    SAFETY_INFO_ELEMENTS,
    SAFETY_INFO_ATTRIBUTES,
    SECURITY_ATTRIBUTES,
    SECURITY_ELEMENTS,
)
from .reference import ReferenceType
from .spec import AttributeSpec, ElementSpec

__all__ = [
    "AttributeSpec",
    "ElementSpec",
    "CONTROLLER_ATTRIBUTES",
    "CONTROLLER_ELEMENTS",
    "PRIMARY_ACTION_SET_ATTRIBUTES",
    "REDUNDANCY_INFO_ATTRIBUTES",
    "ReferenceType",
    "SECURITY_ATTRIBUTES",
    "SECURITY_ELEMENTS",
    "SAFETY_INFO_ATTRIBUTES",
    "SAFETY_INFO_ELEMENTS",
]
