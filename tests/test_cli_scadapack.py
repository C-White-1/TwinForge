"""Public read-only SCADAPack .RCZ/.STA inspection contract."""
from io import BytesIO, StringIO
import json
from pathlib import Path
import zipfile

from twinforge.cli import main


def _station_ctx(pairs: dict[str, str]) -> bytes:
    out = bytearray()
    for name, value in pairs.items():
        for text in (name, value):
            out += b"\xff\xfe\xff" + bytes([len(text)]) + text.encode("utf-16-le")
    return bytes(out)


def _rcz(members: dict[str, bytes]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buf.getvalue()


def _sta(members: dict[str, bytes]) -> bytes:
    return _rcz(members)


def test_inspects_station_properties_as_json(tmp_path: Path):
    path = tmp_path / "demo.RCZ"
    path.write_bytes(_rcz({"demo.STA": _sta({
        "STATION.CTX": _station_ctx({"APPLICATION LIBSET": "V15.1", "PROCESSOR": "SCADAPack47x"}),
    })}))
    output = StringIO()

    assert main(("scadapack", "inspect", str(path), "--format", "json"), stdout=output) == 0

    report = json.loads(output.getvalue())
    assert report["status"] == "inspected"
    assert report["station_properties"]["PROCESSOR"] == "SCADAPack47x"
    assert report["routines"] == []
    assert report["device_type_managers"] == []


def test_inspects_station_properties_as_text(tmp_path: Path):
    path = tmp_path / "demo.RCZ"
    path.write_bytes(_rcz({"demo.STA": _sta({
        "STATION.CTX": _station_ctx({"APPLICATION LIBSET": "V15.1", "PROCESSOR": "SCADAPack47x",
                                     "STU COMPATIBILITY LEVEL": "109", "PLC ADDRESS": "10.2.3.4:504",
                                     "PLC MEDIA": "TCPIP"}),
    })}))
    output = StringIO()

    assert main(("scadapack", "inspect", str(path)), stdout=output) == 0

    text = output.getvalue()
    assert "RTU model: SCADAPack47x" in text
    assert "Application LIBSET: V15.1" in text
    assert "PLC address: 10.2.3.4:504 (TCPIP)" in text


def test_no_supported_content_is_a_clean_failure(tmp_path: Path):
    path = tmp_path / "demo.RCZ"
    path.write_bytes(_rcz({"demo.STA": _sta({"version.txt": b"nothing useful"})}))
    output = StringIO()
    errors = StringIO()

    assert main(("scadapack", "inspect", str(path)), stdout=output, stderr=errors) == 1
    assert "no supported SCADAPack content found" in errors.getvalue()


def test_missing_input_has_a_clean_error(tmp_path: Path):
    output = StringIO()
    errors = StringIO()

    assert main(("scadapack", "inspect", str(tmp_path / "missing.RCZ")), stdout=output, stderr=errors) == 1
    assert not output.getvalue()
    assert "could not inspect SCADAPack input" in errors.getvalue()
