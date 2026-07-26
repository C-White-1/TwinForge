from twinforge.knowledge.logix_types import logix_builtin_types


def test_logix_builtin_types_have_provenance_and_expected_members():
    types = {item.name: item for item in logix_builtin_types()}

    assert set(types) == {"TIMER", "FBD_TIMER", "STRING", "MESSAGE"}
    assert all(item.vendor == "Rockwell Automation" for item in types.values())
    assert all(item.source for item in types.values())
    assert {
        member.name: (member.data_type, member.dimensions)
        for member in types["STRING"].members
    } == {
        "LEN": ("DINT", "0"),
        "DATA": ("SINT", "82"),
    }
    assert types["MESSAGE"].complete is False
