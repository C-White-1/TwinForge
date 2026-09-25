"""SCADAPack `.RCZ`/`.STA` capture: container walk, zlib streams, STATION.CTX."""
from io import BytesIO
import zipfile
import zlib

from twinforge.parsers.scadapack.capture import capture_bytes


def _station_ctx(pairs: dict[str, str]) -> bytes:
    out = bytearray()
    for name, value in pairs.items():
        for text in (name, value):
            out += b"\xff\xfe\xff" + bytes([len(text)]) + text.encode("utf-16-le")
    return bytes(out)


def _st_exchange_xml(source: str) -> bytes:
    return (
        '<?xml version="1.0" standalone="yes"?>\r\n'
        f'<STExchangeFile><STSource>{source}</STSource>'
        '<D1 c14="1"><D0 k="8" O0="0"/><D0 k="20" O0="1"/></D1></STExchangeFile>'
    ).encode()


def _apd(*chunks: bytes) -> bytes:
    # The real shell has an undecoded binary preamble; a few junk bytes here
    # stand in for it -- the scan works purely off zlib header bytes, so the
    # exact preamble content is irrelevant to what's under test.
    return b"\x00\x00\x00\x00" + b"".join(zlib.compress(c) for c in chunks)


def _sta(members: dict[str, bytes]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buf.getvalue()


def _rcz(members: dict[str, bytes]) -> bytes:
    return _sta(members)  # identical shape at this level: an ordinary ZIP


def test_finds_plain_xml_structured_text_inside_nested_archives():
    apd = _apd(_st_exchange_xml("x := 1;"))
    ctx = _station_ctx({"APPLICATION LIBSET": "V15.1"})
    sta = _sta({"BinAppli/Station.apd": apd, "STATION.CTX": ctx})
    rcz = _rcz({"demo.STA": sta, "version.txt": b"whatever"})

    captured = capture_bytes(rcz, name="demo.RCZ")

    assert captured.kind == "archive"
    sta_artifact = next(m for m in captured.members if m.name == "demo.STA")
    apd_artifact = next(m for m in sta_artifact.members if m.name == "BinAppli/Station.apd")
    assert apd_artifact.kind == "zlib_container"
    stream = apd_artifact.members[0]
    assert stream.kind == "structured_text"
    assert stream.content_label == "STExchangeFile"
    assert stream.section is not None
    st_source = next(c for c in stream.section.ordered_children if c.tag == "STSource")
    assert st_source.text == "x := 1;"
    ctx_artifact = next(m for m in sta_artifact.members if m.name == "STATION.CTX")
    assert ctx_artifact.kind == "station_properties"
    assert ctx_artifact.station_properties == {"APPLICATION LIBSET": "V15.1"}


def test_multiple_zlib_streams_in_one_member_are_all_found_and_deduplicated():
    apd = _apd(_st_exchange_xml("a := 1;"), _st_exchange_xml("b := 2;"))
    captured = capture_bytes(_sta({"BinAppli/Station.apd": apd}), name="only.STA")

    apd_artifact = captured.members[0]
    assert apd_artifact.kind == "zlib_container"
    assert len(apd_artifact.members) == 2
    texts = []
    for member in apd_artifact.members:
        assert member.section is not None
        texts.append(next(c for c in member.section.ordered_children if c.tag == "STSource").text)
    assert texts == ["a := 1;", "b := 2;"]


def test_non_xml_stream_with_a_recognizable_label_is_diagnosed_not_guessed():
    # Stands in for the real .NET-framed shape: content this project cannot
    # actually decode, but can still recognize by a content marker.
    binary_framed = b"\x01\x02STExchangeFile\x03\x04garbage-not-xml"
    apd = _apd(binary_framed)
    captured = capture_bytes(_sta({"BinAppli/Station.apd": apd}), name="only.STA")

    stream = captured.members[0].members[0]
    assert stream.kind == "binary_framed"
    assert stream.content_label == "STExchangeFile"
    assert any(d.code == "unsupported_binary_framed_stream" for d in stream.diagnostics)
    assert stream.section is None


def test_unrecognizable_non_xml_stream_is_retained_opaque():
    apd = _apd(b"\x01\x02\x03 nothing recognizable here \x04\x05")
    captured = capture_bytes(_sta({"BinAppli/Station.apd": apd}), name="only.STA")

    stream = captured.members[0].members[0]
    assert stream.kind == "opaque"
    assert stream.content_label is None


def test_member_with_no_zlib_streams_is_opaque_not_misclassified():
    captured = capture_bytes(_sta({"version.txt": b"plain text, not a zlib shell"}), name="only.STA")

    member = captured.members[0]
    assert member.kind == "opaque"
    assert member.members == []


def test_xml_member_with_a_utf8_bom_is_still_recognized():
    data = b"\xef\xbb\xbf<?xml version=\"1.0\"?><FdtDtmProject/>"
    captured = capture_bytes(_sta({"demo.PRJ": data}), name="only.STA")

    member = captured.members[0]
    assert member.kind == "xml"
    assert member.content_label == "FdtDtmProject"


def test_station_ctx_with_broken_framing_is_diagnosed_not_silently_empty():
    captured = capture_bytes(_sta({"STATION.CTX": b"not the right framing at all"}), name="only.STA")

    member = captured.members[0]
    assert member.kind == "opaque"
    assert member.station_properties is None
    assert any(d.code == "unresolved_station_ctx_framing" for d in member.diagnostics)


def test_capture_is_deterministic():
    apd = _apd(_st_exchange_xml("x := 1;"))
    rcz = _rcz({"demo.STA": _sta({"BinAppli/Station.apd": apd})})

    first = capture_bytes(rcz, name="demo.RCZ")
    second = capture_bytes(rcz, name="demo.RCZ")

    def names(artifact):
        return (artifact.name, artifact.kind, [names(m) for m in artifact.members])

    assert names(first) == names(second)
