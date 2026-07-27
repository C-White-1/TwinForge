from twinforge.analysis import ParameterSetpointBinding
from twinforge.assembly.software_devices import _configured_parameter_value
from twinforge.model import (
    AddOnInstruction,
    AddOnInstructionParameter,
    SourceExtension,
    SourceNode,
    Tag,
)


def _instance_tag(*members: SourceNode) -> Tag:
    return Tag(
        name="Dvc",
        source_extensions=[
            SourceExtension(
                format="l5x",
                root=SourceNode(
                    name="Tag",
                    children=[
                        SourceNode(
                            name="Data",
                            attributes={"Format": "Decorated"},
                            children=[
                                SourceNode(
                                    name="Structure",
                                    children=list(members),
                                )
                            ],
                        )
                    ],
                ),
            )
        ],
    )


def _member(name: str, value: str) -> SourceNode:
    return SourceNode(
        name="DataValueMember",
        attributes={
            "Name": name,
            "DataType": "REAL",
            "Radix": "Float",
            "Value": value,
        },
    )


def test_extracts_unique_configured_member_by_original_aoi_label():
    result = _configured_parameter_value(
        _instance_tag(_member("Cfg_MotorNPFLA", "2.5")),
        "P034 [MotorNPFLA]",
    )

    assert result is not None
    assert result.lexical_value == "2.5"
    assert result.source == "Dvc.Cfg_MotorNPFLA"
    assert result.data_type == "REAL"
    assert result.radix == "Float"


def test_does_not_promote_ambiguous_or_unlabelled_values():
    tag = _instance_tag(
        _member("Cfg_MotorNPFLA", "2.5"),
        _member("Cfg_MotorNPFLA", "3.0"),
    )

    assert _configured_parameter_value(tag, "P034 [MotorNPFLA]") is None
    assert _configured_parameter_value(tag, None) is None


def test_follows_exact_aoi_setpoint_alias_when_public_name_differs():
    implementation = AddOnInstruction(name="Drive")
    implementation.add_parameter(
        AddOnInstructionParameter(
            name="Cfg_AccelTime",
            alias_for="Local.Params.AccelTime1.SP",
        )
    )

    result = _configured_parameter_value(
        _instance_tag(_member("Cfg_AccelTime", "10.0")),
        "P041 [AccelTime1]",
        implementation,
    )

    assert result is not None
    assert result.lexical_value == "10.0"
    assert result.source == "Dvc.Cfg_AccelTime"


def test_reads_exact_nested_setpoint_when_no_public_alias_exists():
    implementation = AddOnInstruction(name="Drive")
    tag = _instance_tag(
        SourceNode(
            name="StructureMember",
            attributes={"Name": "Opto1Level"},
            children=[_member("SP", "1")],
        )
    )

    result = _configured_parameter_value(
        tag,
        "T070 [OptoOut1Level]",
        implementation,
        ParameterSetpointBinding(
            number=70,
            member_name="Opto1Level",
            routine_name="Logic",
            evidence="WriteInstance := 70;",
        ),
    )

    assert result is not None
    assert result.lexical_value == "1"
    assert result.source == "Dvc.Opto1Level.SP"
