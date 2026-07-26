# PLCopen XML references

TwinForge targets PLCopen XML version 2.01, using the namespace
`http://www.plcopen.org/xml/tc6_0201`.

The reference documents and XML Schema were obtained from the official PLCopen
downloads page:

- <https://www.plcopen.org/downloads/>

They were downloaded on 21 July 2026 and are stored locally in the ignored
directory `reference/PLCopenXML/standard/`:

- `pdfs/plcopen_xml_exchange (1).pdf`
- `pdfs/tc6_xml_v201_technical_doc (1).pdf`
- `pdfs/tc6_xml_v201_xsd (1).pdf`
- `tc6_xml_v201.xsd`

The local XSD is used as the authoritative development and validation reference.
The `reference/` directory is intentionally excluded from version control.
TwinForge must not redistribute these source documents or the XSD until their
redistribution terms have been confirmed. Released software should either accept
an externally supplied schema for validation or link users to the official
PLCopen download.

Native CODESYS exports used to understand its PLCopen XML extensions are kept
separately under the ignored directory
`reference/PLCopenXML/codesys-native/`. They are implementation evidence, not
TwinForge-generated examples.

### CODESYS high-resolution real-time clock evidence

The native `08_rtc_high_res.xml` experiment was exported from CODESYS V3.5
SP22 Patch 2. It establishes the CODESYS representation needed for a future
wall-clock adapter:

- the POU is stored in the CODESYS application extension rather than the
  standard top-level `types/pous` collection;
- `SysTime` and `SysTypes.RTS_IEC_RESULT` are emitted as derived types;
- the Structured Text body preserves
  `SysTimeRtcHighResGet(stUtcMilliseconds)` and the conversion to
  `LDATE_AND_TIME` verbatim in XHTML;
- the library metadata includes the `SysTimeRtc` placeholder, `SysTime`
  version 3.5.17.0, and `SysTypes2 Interfaces` under the `SysTypes`
  namespace.

`SysTimeRtcHighResGet` supplies UTC milliseconds since the Unix epoch. A
Rockwell `GSV(WallClockTime, ..., CurrentValue, ...)` value is expressed in
microseconds, so equivalent elapsed-time logic must normalize units rather
than copy the original multiplication unchanged.

The subsequent native `09_rtc_pulse.xml` experiment establishes the complete
stateful function-block pattern:

- `FB_RtcPulseGen` is emitted as a CODESYS application-extension POU with
  `pouType="functionBlock"`;
- inputs, outputs, and retained instance-local variables occupy their
  corresponding PLCopen interface sections;
- `PLC_PRG` declares the function-block instance as a derived type;
- the ST invocation uses `:=` for inputs and `=>` for outputs;
- cold-start initialization is represented by ordinary initial values, while
  the previous-enable flag and interval start remain function-block state.

This is sufficient target evidence for a CODESYS wall-clock and pulse-generator
adapter. TwinForge must still introduce a general AOI-to-IEC Structured Text
transformation boundary before emitting this pattern; it should not special
case an AOI named `RTC_PulseGen`.

For the currently implemented L5X conversion and CODESYS compatibility
boundary, see [L5X to PLCopen XML capability matrix](../plcopen-capabilities.md).
