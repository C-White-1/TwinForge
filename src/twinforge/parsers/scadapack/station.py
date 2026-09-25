"""Map captured SCADAPack content into vendor-neutral model objects.

Milestone 1 only (docs/roadmaps/scadapack-rcz-capture-roadmap.md): a
plain-XML `STExchangeFile`/`STSource` stream becomes an ordinary `Routine`
(`language="ST"`) -- the same `StructuredTextLine` model Control Expert's
own ST bodies already use, since what container the source came from
doesn't change what a line of Structured Text is. Everything else this
format's capture layer recognizes (binary-framed streams, FBD, `.prj`
DTM/comm-channel content, the `D1` per-statement offset table) is retained
as capture evidence but not interpreted here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from twinforge.model import Routine, StructuredTextLine

from .capture import CapturedArtifact, Diagnostic
from .evidence import source_extension as _extension


@dataclass
class ParsedStation:
    artifact: CapturedArtifact
    station_properties: dict[str, str] = field(default_factory=dict)
    routines: list[Routine] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def report(self, code: str, message: str, source_artifact: CapturedArtifact) -> None:
        self.diagnostics.append(Diagnostic(code, message, source_artifact.source))


def _st_source_text(artifact: CapturedArtifact) -> str:
    assert artifact.section is not None
    for child in artifact.section.ordered_children:
        if child.tag == "STSource":
            return child.text or ""
    return ""


def _routine(artifact: CapturedArtifact) -> Routine:
    assert artifact.section is not None
    text = _st_source_text(artifact)
    return Routine(
        name=artifact.name, language="ST",
        structured_text_lines=[
            StructuredTextLine(number=index + 1, text=line)
            for index, line in enumerate(text.split("\n"))
        ],
        source_extensions=[_extension(artifact.section, artifact.source)],
    )


def _walk(artifact: CapturedArtifact, result: ParsedStation) -> None:
    if artifact.kind == "station_properties" and artifact.station_properties:
        if result.station_properties:
            result.report("ambiguous_station_properties",
                          "More than one STATION.CTX found; keeping the first", artifact)
        else:
            result.station_properties = artifact.station_properties
    elif artifact.kind == "structured_text":
        routine = _routine(artifact)
        if not any(line.text.strip() for line in routine.structured_text_lines):
            result.report("empty_structured_text_stream", "STExchangeFile stream has no source text", artifact)
        result.routines.append(routine)
    for member in artifact.members:
        _walk(member, result)


def parse_station(artifact: CapturedArtifact) -> ParsedStation:
    """Map one captured `.RCZ`/`.STA` artifact into its ST-only station content.

    Every `structured_text` stream found anywhere in the captured tree
    becomes its own `Routine` -- a single RTU can (and, per the real
    corpus, usually does) hold several independent ST sections, with no
    reliable name evidence beyond the stream's own capture-layer identity
    (`stream[N]@0xOFFSET`), so that identity is what `Routine.name` carries;
    fabricating a nicer name would misrepresent what is actually known.
    """
    result = ParsedStation(artifact, diagnostics=list(artifact.diagnostics))
    _walk(artifact, result)
    if not result.station_properties:
        result.report("missing_station_properties", "No STATION.CTX found; RTU model/version unknown", artifact)
    if not result.routines:
        result.report("no_structured_text_found",
                      "No plain-XML STExchangeFile stream found -- either none exists in this "
                      "input, or its STSource uses the older binary-framed shape this project "
                      "does not decode yet", artifact)
    return result
