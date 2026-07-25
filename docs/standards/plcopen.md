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

For the currently implemented L5X conversion and CODESYS compatibility
boundary, see [L5X to PLCopen XML capability matrix](../plcopen-capabilities.md).
