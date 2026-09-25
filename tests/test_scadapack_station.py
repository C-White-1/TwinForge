"""SCADAPack station mapping: plain-XML STSource streams to Routines."""
from io import BytesIO
import zipfile
import zlib

from twinforge.parsers.scadapack.capture import capture_bytes
from twinforge.parsers.scadapack.station import parse_station


def _station_ctx(pairs: dict[str, str]) -> bytes:
    out = bytearray()
    for name, value in pairs.items():
        for text in (name, value):
            out += b"\xff\xfe\xff" + bytes([len(text)]) + text.encode("utf-16-le")
    return bytes(out)


def _st_exchange_xml(source: str) -> bytes:
    return (
        '<?xml version="1.0" standalone="yes"?>\r\n'
        f'<STExchangeFile><STSource>{source}</STSource></STExchangeFile>'
    ).encode()


def _apd(*chunks: bytes) -> bytes:
    return b"\x00\x00\x00\x00" + b"".join(zlib.compress(c) for c in chunks)


def _sta(members: dict[str, bytes]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buf.getvalue()


def station(members: dict[str, bytes]):
    return parse_station(capture_bytes(_sta(members), name="demo.STA"))


def test_st_stream_and_station_properties_resolve_together():
    result = station({
        "BinAppli/Station.apd": _apd(_st_exchange_xml("x := 1;\ny := 2;")),
        "STATION.CTX": _station_ctx({"APPLICATION LIBSET": "V15.1", "PROCESSOR": "SCADAPack47x"}),
    })

    assert result.station_properties == {"APPLICATION LIBSET": "V15.1", "PROCESSOR": "SCADAPack47x"}
    assert len(result.routines) == 1
    routine = result.routines[0]
    assert routine.language == "ST"
    assert routine.structured_text == "x := 1;\ny := 2;"
    assert routine.source_extensions[0].format == "scadapack"
    assert not any(d.code.startswith("missing_") or d.code.startswith("no_") for d in result.diagnostics)


def test_multiple_streams_become_multiple_independently_named_routines():
    result = station({
        "BinAppli/Station.apd": _apd(_st_exchange_xml("a := 1;"), _st_exchange_xml("b := 2;")),
    })

    assert len(result.routines) == 2
    assert result.routines[0].name != result.routines[1].name
    assert {r.structured_text for r in result.routines} == {"a := 1;", "b := 2;"}


def test_missing_station_properties_and_missing_st_are_both_diagnosed():
    result = station({"version.txt": b"nothing useful here"})

    assert result.station_properties == {}
    assert result.routines == []
    codes = {d.code for d in result.diagnostics}
    assert "missing_station_properties" in codes
    assert "no_structured_text_found" in codes


def test_old_binary_framed_fixture_reports_no_structured_text_not_a_guess():
    binary_framed = b"\x01\x02STExchangeFile\x03\x04garbage-not-xml"
    result = station({"BinAppli/Station.apd": _apd(binary_framed)})

    assert result.routines == []
    assert any(d.code == "no_structured_text_found" for d in result.diagnostics)


def test_empty_st_source_text_is_diagnosed():
    result = station({"BinAppli/Station.apd": _apd(_st_exchange_xml(""))})

    assert len(result.routines) == 1
    assert any(d.code == "empty_structured_text_stream" for d in result.diagnostics)


def test_mapping_is_deterministic():
    members = {
        "BinAppli/Station.apd": _apd(_st_exchange_xml("x := 1;")),
        "STATION.CTX": _station_ctx({"APPLICATION LIBSET": "V15.1"}),
    }
    data = _sta(members)

    first = parse_station(capture_bytes(data, name="demo.STA"))
    second = parse_station(capture_bytes(data, name="demo.STA"))

    assert [r.structured_text for r in first.routines] == [r.structured_text for r in second.routines]
    assert first.station_properties == second.station_properties
