from twinforge.exporters import ParameterMarkdownExporter
from twinforge.model import Device, ObservedParameterAccess


def test_exports_observed_parameter_inventory():
    device = Device(name="Drive")
    device.observed_parameters = [
        ObservedParameterAccess(
            number=38,
            label="P038 [VoltageClass]",
            code="P038",
            group_prefix="P",
            group_name="Basic Program",
            display_name="VoltageClass",
            observed_read=True,
            read_buffer_indices=(17,),
            evidence=("Ref_MsgData[17] := 38;",),
        ),
        ObservedParameterAccess(
            number=34,
            observed_write=True,
            evidence=("WriteInstance := 34;",),
        ),
    ]

    report = ParameterMarkdownExporter().export(device)

    assert "| ---: | --- | --- | :---: | :---: | :---: | --- |" in report
    assert "|---" not in report
    assert "| 34 | — | — | — | no | yes | — |" in report
    assert (
        "| 38 | P038 | VoltageClass | Basic Program | yes | no | 17 |"
        in report
    )
