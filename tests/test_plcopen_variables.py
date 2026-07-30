import xml.etree.ElementTree as ET

from twinforge.model import Tag, TagValue
from twinforge.exporters.plcopen_variables import PLCopenVariableEmitter


NAMESPACE = "urn:twinforge:test:plcopen"
NS = {"p": NAMESPACE}


def _tag_export_type(tag: Tag) -> str:
    """Supply the effective type normally prepared by the operand plan."""

    return (tag.data_type or "BOOL").upper()


def test_unsupported_and_array_tags_are_diagnosed_in_source_order() -> None:
    diagnostics: list[tuple[str, str | None]] = []

    def report(
        code: str,
        _message: str,
        _object_name: str | None,
        *,
        raw_value: str | None = None,
    ) -> None:
        diagnostics.append((code, raw_value))

    root = ET.Element("root")
    result = PLCopenVariableEmitter(
        namespace=NAMESPACE,
        tag_export_type=_tag_export_type,
        timer_type="TON",
        report_diagnostic=report,
    ).emit(
        root,
        "globalVars",
        [
            Tag(name="Structure", data_type="CustomType"),
            Tag(name="Values", data_type="REAL", dimensions="[10]"),
        ],
    )

    assert result is None
    assert list(root) == []
    assert diagnostics == [
        ("unsupported_variable_type", "CustomType"),
        ("array_variable_not_exported", "[10]"),
    ]


def test_scalar_timer_and_target_derived_types_are_emitted() -> None:
    root = ET.Element("root")
    tags = [
        Tag(
            name="Enabled",
            data_type="BOOL",
            initial_value=TagValue(
                value=True,
                data_type="BOOL",
                lexical_value="1",
            ),
        ),
        Tag(name="Delay", data_type="TIMER"),
        Tag(
            name="Edge",
            data_type="R_TRIG",
            metadata={"plcopen_derived_type": "Standard.R_TRIG"},
        ),
    ]

    PLCopenVariableEmitter(
        namespace=NAMESPACE,
        tag_export_type=_tag_export_type,
        timer_type="Standard.TON",
        report_diagnostic=lambda *_args, **_kwargs: None,
    ).emit(root, "localVars", tags)

    assert root.find(
        ".//p:variable[@name='Enabled']/p:type/p:BOOL",
        NS,
    ) is not None
    assert root.find(
        ".//p:variable[@name='Enabled']/p:initialValue/"
        "p:simpleValue[@value='TRUE']",
        NS,
    ) is not None
    assert root.find(
        ".//p:variable[@name='Delay']/p:type/"
        "p:derived[@name='Standard.TON']",
        NS,
    ) is not None
    assert root.find(
        ".//p:variable[@name='Edge']/p:type/"
        "p:derived[@name='Standard.R_TRIG']",
        NS,
    ) is not None


def test_source_evidence_and_documentation_are_preserved() -> None:
    diagnostics: list[str] = []
    root = ET.Element("root")
    tags = [
        Tag(
            name="InputAlias",
            alias_for="Local:1:I.Data.0",
            description="Start input",
        ),
        Tag(
            name="OneShot",
            data_type="R_TRIG",
            metadata={
                "plcopen_derived_type": "R_TRIG",
                "rockwell_ons_storage": "StorageBit",
            },
        ),
    ]

    PLCopenVariableEmitter(
        namespace=NAMESPACE,
        tag_export_type=_tag_export_type,
        timer_type="TON",
        report_diagnostic=lambda code, *_args, **_kwargs: diagnostics.append(
            code
        ),
    ).emit(root, "globalVars", tags)

    assert diagnostics == ["alias_exported_as_surrogate"]
    alias = root.find(
        ".//p:variable[@name='InputAlias']/p:addData/"
        "p:data[@name='https://twinforge.dev/plcopenxml/rockwell-alias']/"
        "AliasFor",
        NS,
    )
    assert alias is not None and alias.text == "Local:1:I.Data.0"
    storage = root.find(
        ".//p:variable[@name='OneShot']/p:addData/"
        "p:data[@name='https://twinforge.dev/plcopenxml/rockwell-ons']/"
        "StorageOperand",
        NS,
    )
    assert storage is not None and storage.text == "StorageBit"
    assert (
        root.findtext(
            ".//p:variable[@name='InputAlias']/p:documentation/"
            "{http://www.w3.org/1999/xhtml}xhtml",
            namespaces=NS,
        )
        == "Start input"
    )
