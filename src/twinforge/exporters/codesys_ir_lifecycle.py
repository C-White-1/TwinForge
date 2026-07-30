"""CODESYS lifecycle mapping and native method serialization for IEC IR."""

from __future__ import annotations

from collections.abc import Callable
import xml.etree.ElementTree as ET

from twinforge.ir import (
    IRReusableUnit,
    IRRoutine,
    IRRoutineRole,
    IRUnitKind,
)

from .codesys_st import emit_codesys_st_routine
from .plcopen_codesys import CODESYS_NAMESPACE
from .plcopen_types import PLCOPEN_CODESYS_NAMESPACE
from .plcopen_xml import qualified_name as q


XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
ObjectIdProvider = Callable[[str], str]


class CodesysIRLifecycleEmitter:
    """Map supported neutral lifecycle routines to native CODESYS methods."""

    def __init__(self, *, object_id: ObjectIdProvider) -> None:
        self._object_id = object_id

    @staticmethod
    def mapped_prescan(unit: IRReusableUnit) -> IRRoutine | None:
        """Return an enabled Prescan routine eligible for ``FB_Init``."""

        if (
            unit.kind is not IRUnitKind.FUNCTION_BLOCK
            or unit.lifecycle.prescan_enabled is not True
        ):
            return None
        return next(
            (
                routine
                for routine in unit.routines
                if routine.role is IRRoutineRole.PRESCAN
            ),
            None,
        )

    def has_mapped_prescan(self, unit: IRReusableUnit) -> bool:
        """Return whether the unit contributes an ``FB_Init`` method."""

        return self.mapped_prescan(unit) is not None

    def method_object_id(self, unit: IRReusableUnit) -> str:
        """Return the deterministic identity of the mapped method."""

        return self._object_id(
            f"Application/pou/{unit.name}/method/FB_Init"
        )

    def emit(self, add_data: ET.Element, unit: IRReusableUnit) -> None:
        """Append the supported lifecycle method, when one is enabled."""

        routine = self.mapped_prescan(unit)
        if routine is None:
            return
        self._prescan_method(add_data, unit, routine)

    def _prescan_method(
        self,
        add_data: ET.Element,
        unit: IRReusableUnit,
        routine: IRRoutine,
    ) -> None:
        ns = PLCOPEN_CODESYS_NAMESPACE
        data = ET.SubElement(
            add_data,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/method",
                "handleUnknown": "implementation",
            },
        )
        method = ET.SubElement(
            data,
            q(ns, "Method"),
            {
                "name": "FB_Init",
                "ObjectId": self.method_object_id(unit),
            },
        )
        interface = ET.SubElement(method, q(ns, "interface"))
        return_type = ET.SubElement(interface, q(ns, "returnType"))
        ET.SubElement(return_type, q(ns, "BOOL"))
        inputs = ET.SubElement(interface, q(ns, "inputVars"))
        for name in ("bInitRetains", "bInCopyCode"):
            variable = ET.SubElement(
                inputs,
                q(ns, "variable"),
                {"name": name},
            )
            type_element = ET.SubElement(variable, q(ns, "type"))
            ET.SubElement(type_element, q(ns, "BOOL"))
        body = ET.SubElement(method, q(ns, "body"))
        st = ET.SubElement(body, q(ns, "ST"))
        text = ET.SubElement(st, q(XHTML_NAMESPACE, "xhtml"))
        emitted = emit_codesys_st_routine(routine).text.rstrip()
        text.text = f"{emitted}\nFB_Init := TRUE;"
        ET.SubElement(method, q(ns, "addData"))
