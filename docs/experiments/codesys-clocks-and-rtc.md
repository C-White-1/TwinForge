# CODESYS clocks and real-time clock (for `%S4`–`%S7`, `%SW49`–`%SW53`)

**Question:** what in CODESYS reproduces Machine Expert – Basic's clock bits
and real-time-clock words?

- **Run:** 2026-10-18, by the project owner
- **Environment:** CODESYS V3.5 SP22 Patch 3, Control Win (SoftPLC)

## The M221 side

From the M221 Programming Guide (EIO0000003297.04):

- **Clocks** ("System Bits (%S)"): `%S4`, `%S5`, `%S6`, `%S7` have time
  bases of 10 ms, 100 ms, 1 s and 1 min. "The rate of status changes is
  measured by an internal clock. They are not synchronized with the
  controller scan."
- **Real-time clock** ("System Words (%SW)"): "words containing current
  date and time values (in BCD)": `%SW49` day of the week (1 = Monday,
  read-only), `%SW50` `00SS`, `%SW51` `HHMM`, `%SW52` `MMDD`, `%SW53` `CCYY`.
- **Setting the clock:** with `%S50` = 1 the controller stops updating
  `%SW49`–`%SW53` so the program can write them; on its falling edge it
  sets the clock from them. With `%S59` = 1, rising edges on the bits of
  `%SW59` step each field up or down. `%S51` = 1 means the clock is not
  valid.

## Clocks: `TIME()`

CODESYS's `TIME()` operator returns the time since the runtime started, in
milliseconds, as a 32-bit `TIME`
([CODESYS: operators](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_operands_functions.html)).
A clock with half-period *h* ms is `(ms / h) MOD 2 = 1`. Test code:

```text
nMs := TIME_TO_UDINT(TIME());
x10ms := (nMs / 5) MOD 2 = 1;
x100ms := (nMs / 50) MOD 2 = 1;
x1s := (nMs / 500) MOD 2 = 1;
x1min := (nMs / 30000) MOD 2 = 1;
```

**Result:** builds and runs. Watched online, the bits "seemed a bit slower"
than expected: online monitoring refreshes only every few hundred
milliseconds. Measured with a Trace instead (see the converted test below).

Known limits, by design: the bits are sampled once per scan (the M221
changes them independently of the scan), so a clock faster than the scan
aliases on both; `TIME()` wraps after about 49.7 days, giving one irregular
half-period.

## Real-time clock: `SysTimeRtc`

The system library SysTimeRtc 3.5.22.0 (System), added with Library
Manager → Add Library, offers (from its Library Manager page):

| Function | Inputs/outputs |
| --- | --- |
| `SysTimeRtcGet : DWORD` | `pResult` (IN_OUT `RTS_IEC_RESULT`); returns UTC seconds since 1970 |
| `SysTimeRtcConvertUtcToLocal : RTS_IEC_RESULT` | `dwTimestampUtc : DWORD`, `pdwTimestampLocal` (IN_OUT `DWORD`) |
| `SysTimeRtcConvertUtcToDate : RTS_IEC_RESULT` | `dwTimestampUtc : DWORD`, `pDate` (IN_OUT `SYSTIMEDATE`) |
| `SysTimeRtcHighResGet : RTS_IEC_RESULT` | `pTimestamp` (IN_OUT `SYSTIME`, ms since 1970 UTC) |
| `SysTimeRtcConvertHighResToLocal : RTS_IEC_RESULT` | `pTimestamp` (IN_OUT `SYSTIME`), `pDate` (IN_OUT `SYSTIMEDATE`, local time) |

**Library Manager entry**, from CODESYS's PLCopen export of the Library
Manager: a placeholder, `<Library Name="#SysTimeRtc" Namespace="SysTimeRtc"
... DefaultResolution="SysTimeRtc, * (System)" />` (any installed version).

`SYSTIMEDATE` (`RTS_SYSTIMEDATE`) has `wYear`, `wMonth`, `wDay`, `wHour`,
`wMinute`, `wSecond`, `wMilliseconds`, `wDayOfWeek` ("Monday = 1, Sunday =
7", as the M221's `%SW49`) and `wYday`, all `UINT`.

**Types:** `RTS_IEC_RESULT` and `SYSTIME` are aliases from other system
libraries; with only SysTimeRtc referenced the build reports "Unknown type"
(C0077) and names the types underneath: `UDINT` and `ULINT`. Declared as
those, it builds.

**Test code** (standard route: UTC seconds → local seconds → fields; the
local seconds are split into fields, so the fields are local time):

```text
dwUtc := SysTimeRtcGet(pResult := eResult);
eLocal := SysTimeRtcConvertUtcToLocal(dwTimestampUtc := dwUtc, pdwTimestampLocal := dwLocal);
eDate := SysTimeRtcConvertUtcToDate(dwTimestampUtc := dwLocal, pDate := stStd);
```

plus the high-resolution route (`SysTimeRtcHighResGet`,
`SysTimeRtcConvertHighResToLocal`) and the BCD words. **Result:** "RTC is
working fine". Whether the high-resolution route's day of month was
checked before about 10–11 am (a third-party report says it is wrong in
time zones ahead of UTC) was not recorded; TwinForge uses the standard
route.

## The converted test

TwinForge's CODESYS export now adds `TF_StartOfScan`, called first in the
task, when the logic uses these objects: the clocks from `TIME()`, the RTC
words from SysTimeRtc by the standard route, in BCD, written only when all
three calls return 0 and, if the logic uses `%S50`, only while it is FALSE.
Each object gets a `runtime_object_reproduced` diagnostic.

Run on 2026-10-18 with fixture 14 plus ten rungs (each clock bit and
`%S50` to a coil; each RTC word compared with 0), imported into a new
project:

- **Builds,** with the `#SysTimeRtc` placeholder TwinForge writes.
- **RTC words** (hexadecimal display) matched the PC's date and time.
- **`%S50`:** with `SB_RTCUPDATE` TRUE the words stopped updating, and
  resumed when it was set FALSE, as the guide describes ("Set to 1, the date
  and time can be updated but not read"). Basic's own comment on the bit,
  "Set to 1, this bit allows to update the date and time", means the
  program updating the clock.
- **Clocks,** recorded with a Trace on `MAST`: `SB_TB1S` changed about every
  0.5 s (cursors on equal values about 1.03 s apart, within one sample);
  `SB_TB1MIN` was FALSE from 1m30s to 2m of trace time, exactly 30 s, then
  TRUE. The edges fell on whole 30 s marks of the trace's time axis.
- **Sampling:** the trace's samples of the freewheeling `MAST` were uneven,
  with gaps of a few hundred milliseconds; the trace joins them with sloping
  lines. Its buffer (5000 records) held about 40 s.

## Not yet established

- **`%S4` and `%S5` (10 ms, 100 ms):** faster than the trace's sampling;
  not measured. Same formula as the measured ones.
- **Setting the clock** (`%S50` falling edge, `%S59`/`%SW59`): on Control
  Win it would set the Windows clock; to be tried on a separate device (a
  virtual machine or a Raspberry Pi).
