from twinforge.analysis import (
    AlarmTripCandidateKind,
    TagDependencyGraph,
    TagReference,
    TagReferenceAccess,
    build_alarm_trip_candidate_report,
)
from twinforge.model import Controller, Identity, SoftwareTagScope, Tag


def test_selects_only_explicit_alarm_and_trip_evidence() -> None:
    controller = Controller(name="PLC", identity=Identity())
    controller.add_tag(Tag(name="Alm_Fire", description="Fire Detector Alarm"))
    controller.add_tag(
        Tag(name="VibrationTrip", description="Compressor Vibration Trip")
    )
    controller.add_tag(Tag(name="PT102_HH", description="High high pressure"))
    graph = TagDependencyGraph(
        references=(
            TagReference(
                tag_key="controller:VibrationTrip",
                tag_name="VibrationTrip",
                tag_scope=SoftwareTagScope.CONTROLLER,
                member_path=None,
                access=TagReferenceAccess.WRITE,
                instruction="OTE",
                argument_position=0,
                operand="VibrationTrip",
                program_name="Main",
                routine_name="Trips",
                rung_number=3,
                line_number=None,
            ),
        ),
        unresolved_references=(),
    )

    report = build_alarm_trip_candidate_report(controller, graph)

    assert [item.tag_name for item in report.candidates] == [
        "Alm_Fire",
        "VibrationTrip",
    ]
    trip = report.candidates[1]
    assert trip.kinds == (AlarmTripCandidateKind.TRIP,)
    assert trip.writer_locations == ("Main.Trips: rung 3",)
    assert all(item.tag_name != "PT102_HH" for item in report.candidates)


def test_candidate_can_retain_both_explicit_alarm_and_trip_meanings() -> None:
    controller = Controller(name="PLC", identity=Identity())
    controller.add_tag(
        Tag(name="PumpTripAlarm", description="Trip alarm annunciation")
    )

    candidate = build_alarm_trip_candidate_report(controller).candidates[0]

    assert candidate.kinds == (
        AlarmTripCandidateKind.ALARM,
        AlarmTripCandidateKind.TRIP,
    )
    assert len(candidate.classification_evidence) == 4
