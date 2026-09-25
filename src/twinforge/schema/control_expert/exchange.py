"""Observed grammar only; unknown content is always retained by capture."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ElementSpec:
    name: str
    attributes: frozenset[str] = frozenset()
    children: tuple["ElementSpec", ...] = ()
    root_aliases: tuple[str, ...] = ()
    evidence: str = "docs/architecture/control-expert-exchange-capture.md"
    status: str = field(default="observed", init=False)


def element(name: str, attributes: str = "", *children: ElementSpec) -> ElementSpec:
    return ElementSpec(name, frozenset(attributes.split()), children)


_POSITION = element("objPosition", "posX posY")
_REFERENCE = (element("variableName"), element("sectionName"))
_SFC = element("SFCProgram", "areaNum operatorCtrl",
    element("identProgram", "name type task SectionOrder"),
    element("chartSource", "name", element("networkSFC", "",
        element("step", "stepType stepName", _POSITION,
            element("action", "qualifier", element("actionName", "", *_REFERENCE),
                element("tValue", "", element("tLiteral"))),
            element("literals", "max min delay")),
        element("transition", "", _POSITION,
            element("transitionCondition", "invertLogic", *_REFERENCE)),
        element("altBranch", "width relativePos", _POSITION),
        element("linkSFC", "",
            element("directedLinkSource", "objectType", _POSITION),
            element("directedLinkDestination", "objectType", _POSITION),
            element("gridObjPosition", "posX posY")))),
    element("transitionSource", "name", element("STSource")))


_EXCHANGE_SPEC = element(
    "FEFExchangeFile", "",
    element("fileHeader", "company product dateTime content DTDVersion"),
    element("contentHeader", "name version dateTime"),
    _SFC,
    element("commParameters"),
    element("IOConf"),
    element("EFSource", "nameOfEFType version dateTime"),
    element("EFBSource", "nameOfEFBType version dateTime"),
    element("dataBlock", "", element(
        "variables", "name typeName topologicalAddress",
        element("comment"), element("variableInit", "value"),
        element("instanceElementDesc", "name", element("value")),
        element("attribute", "name value"),
    )),
    element("logicConf", "", element(
        "resource", "resName resIdent",
        element("taskDesc", "task taskType valueType maxExecTime",
                element("sectionDesc", "name activationCondition logicCondition")),
        element("FMDesc", "name FMId"),
    )),
    element("program", "", element("identProgram", "name type task"),
            element("STSource"), element("LDSource", "nbColumns"),
            element("FBDSource")),
    element("animationTable", "name location version dateTime ExtStringAnim ExtStringAnimLen"),
    element("Motion"), element("comm"), element("IOScreen", "version"),
    element("Documentation", "version"), element("DTMConfiguration"),
    element("settings", "version"),
)

EXCHANGE_SPEC = ElementSpec(
    _EXCHANGE_SPEC.name, _EXCHANGE_SPEC.attributes, _EXCHANGE_SPEC.children,
    root_aliases=("ZEFExchangeFile",),
)

# A standalone Derived Function Block export (.xdb/.XDB): one `FBSource` at
# the document root instead of embedded as a sibling of `program`/`DDTSource`
# inside a project. Confirmed the same `fileHeader`/`contentHeader` attribute
# shape as FEFExchangeFile (both carry DTDVersion="41" -- the same DTD
# generation, not merely a similarly-named format) and the identical
# FBSource/FBProgram/STSource/FBDSource grammar the embedded-DFB mapping in
# project.py already parses -- so this is a distinct root, not an alias of
# EXCHANGE_SPEC: an .xdb document has no program/logicConf/dataBlock/hardware
# content at all, unlike ZEFExchangeFile, which really is just a zipped
# repackaging of the identical FEFExchangeFile shape.
FB_EXCHANGE_SPEC = ElementSpec(
    "FBExchangeFile", frozenset(), (
        element("fileHeader", "company product dateTime content DTDVersion"),
        element("contentHeader", "name version dateTime"),
        element("FBSource", "nameOfFBType version dateTime"),
    ),
)
