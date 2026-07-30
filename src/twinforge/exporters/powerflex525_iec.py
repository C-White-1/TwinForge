"""Compatibility imports for PowerFlex IEC and CODESYS composition APIs."""

from twinforge.targets.codesys.powerflex525 import (
    PowerFlex525CodesysDevice,
    powerflex525_codesys_application_integration,
    powerflex525_codesys_integration,
    powerflex525_codesys_multi_application_integration,
)

from .powerflex525_core import build_powerflex525_iec_unit

__all__ = [
    "PowerFlex525CodesysDevice",
    "build_powerflex525_iec_unit",
    "powerflex525_codesys_application_integration",
    "powerflex525_codesys_integration",
    "powerflex525_codesys_multi_application_integration",
]
