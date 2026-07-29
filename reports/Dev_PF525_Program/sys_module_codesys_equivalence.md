# CODESYS module-service equivalence

Profile: `ethernet_ip_remote_adapter`. Support and semantic equivalence are classified independently.

| Rockwell intent | CODESYS evidence | Support | Equivalence |
| --- | --- | --- | --- |
| Module instance | `GetDeviceInfo()` identity | Normalized | Approximated |
| `EntryStatus` | `eState` and `GetDeviceState()` | Normalized | Approximated |
| `FaultCode` | CAA Device Diagnosis error | Normalized | Approximated |
| `FaultInfo` | Diagnostic availability and text | Normalized | Approximated |
| Numeric `Mode` | `Enable` and device state | Normalized | Approximated |
| Set inhibited | `Enable`, capability check, and `DED.Reconfigure` | Normalized | Hardware validation required |
| Other source-specific attributes | None established | Unavailable | Unavailable |

No normalized mapping should be interpreted as a raw Rockwell controller-object value.
