# Synthetic EDS evidence

`cip-infrastructure.eds` is a TwinForge-authored test fixture containing the
minimum declarations needed to exercise EDS Assembly connection-path decoding.
It is deliberately independent of vendor reference files, which remain ignored
and are not required by the automated test suite.

The fixture declares one synthetic connection with:

- Assembly class `4`;
- configuration instance `102`;
- originator-to-target connection point `133` and size `496`;
- target-to-originator connection point `132` and size `500`.
