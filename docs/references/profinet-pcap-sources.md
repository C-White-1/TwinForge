# PROFINET PCAP source catalogue

This catalogue records candidate public sources for offline research. Listing
a source does not establish permission to redistribute its captures, prove
that it contains cyclic PROFINET RT, or make it an accepted TwinForge fixture.
Every downloaded artifact requires separate licence, sensitivity, checksum,
and protocol-content review.

## Candidate sources

### ITI ICS-Security-Tools

- Repository: [ITI/ICS-Security-Tools](https://github.com/ITI/ICS-Security-Tools)
- Capture: [profinet.pcap](https://github.com/ITI/ICS-Security-Tools/blob/master/pcaps/profinet/profinet.pcap)
- Reported size: 572 bytes
- Current assessment: suitable only as a possible parser smoke sample; far too
  small for sustained timing or telegram-gap analysis
- Provenance concern: the repository describes the PROFINET material as
  captures from the wild; redistribution and sensitivity require review

### ICS Defense PCAP Archive

- Catalogue: [ICS Defense PCAP Archive](https://icsdefense.net/en/pcap)
- Listed captures: `pro.pcap` and `pro1.pcap` through `pro6.pcap`
- Reported sizes: approximately 211 bytes to 8.75 KiB
- Current assessment: potentially useful for protocol-family decoding, but
  content and licensing must be inspected before acquisition or use

### Medical-waste incinerator SCADA dataset

- Dataset: [Mendeley Data record](https://data.mendeley.com/datasets/vpcr4wpgfd/4)
- Description: 14 daily captures from a Siemens S7-1500/ET200MP installation,
  plus synthetic attack-injected captures
- Paper: [Dataset description](https://pmc.ncbi.nlm.nih.gov/articles/PMC12702041/)
- Current assessment: strongest documented source found, with checksums and
  capture metadata, but its HMI-to-PLC capture position may primarily expose
  S7 or OPC traffic rather than layer-2 cyclic PROFINET RT
- Safety boundary: analyze normal captures first; attack-injected files are
  not required for TwinForge's initial passive engineering use case

### Wireshark developer attachment

- Archive: [PROFINET dissector test discussion](https://lists.wireshark.org/archives/wireshark-dev/200707/msg00303.html)
- Attachment: `profinet_ir_data.pcap`
- Description: three frames supplied for a historical dissector correction
- Current assessment: useful for a narrow decoder regression, not timing

## Official analysis references

- [Wireshark PROFINET/IO wiki](https://wiki.wireshark.org/PROFINET/IO)
- [Wireshark PROFINET IO display fields](https://www.wireshark.org/docs/dfref/p/pn_io.html)
- [Wireshark Ethernet capture guidance](https://wiki.wireshark.org/CaptureSetup/Ethernet)

The Wireshark PROFINET/IO page currently describes an example frame but does
not provide a comprehensive downloadable cyclic capture.

## Local storage convention

Pending review, acquired files should remain outside Git:

```text
reference/PROFINET/PCAP/
├── SOURCES.md
├── manifests/
└── captures/
```

The local `SOURCES.md` should record the exact acquisition date, resolved URL,
licence finding, SHA-256, file size, sanitization review, and intended test or
research purpose. A public URL alone is not permission to redistribute a
packet capture.
