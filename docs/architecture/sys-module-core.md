# Sys_Module portable source semantics

The captured Rockwell `Sys_Module` AOI combines portable status and command
logic with controller-managed `GSV` and `SSV` services. TwinForge separates
those responsibilities.

[`sys_module_core.py`](../../src/twinforge/runtime/sys_module_core.py)
implements the source-equivalent portable behavior:

- Preserve raw instance, EntryStatus, fault code, fault information, and mode
- Decode the high EntryStatus nibble into the documented state flags
- Derive disconnected as neither inhibited nor connected
- Produce a Mode-write intent on a command rising edge
- Preserve the source priority of inhibit over uninhibit
- Clear source outputs during Prescan

The core does not call a Rockwell controller, a CODESYS device object, or any
fieldbus API. A target adapter must supply the raw snapshot and execute or
reject the resulting Mode-write intent.

## Shared command edge

The AOI has one retained `OSR` local tag:

```text
OSR := Inp_Inhibit OR Inp_Uninhibit
```

Consequently, inhibit and uninhibit share one edge detector. Holding a command
does not repeat a write. Switching directly from one command to the other also
does not create a new edge; both inputs must be false for a scan before the
next command can fire. Simultaneous rising commands select inhibit because it
is the first branch in the source `IF`/`ELSIF`.

## Prescan boundary

The source Prescan clears both command inputs, the Status word, and all raw
diagnostic outputs. It does not assign `OSR`. TwinForge therefore clears only
the explicit outputs and reports the source input-reset values without
inventing a retained-latch reset.

## Adapter boundary

`SysModuleRuntime` coordinates the core with the vendor-neutral
`SysModuleAdapter` protocol:

- `read_snapshot()` supplies the attributes consumed by the AOI.
- `write_mode()` applies a requested Mode value.
- Adapter failures become explicit result evidence instead of fabricated
  module values.
- A failed read leaves the previous outputs and one-shot state unchanged.
- A failed write is not retried while the command remains true; the caller
  must release and reassert it to create a new source-compatible edge.

A future CODESYS or EtherNet/IP implementation can satisfy this protocol
without introducing its transport types into the core model. Normalized
diagnostic equivalence and real runtime inhibit behavior still require a
concrete target adapter or physical-device integration test.

## CODESYS normalized adapter

`CodesysEtherNetIPModuleAdapter` implements the narrower neutral
`ModuleService` contract using evidence available from a generated CODESYS
EtherNet/IP remote-adapter object. It exposes normalized connection, enabled,
fault, and diagnostic state. It permits an enable-state request only when the
provider reports `DED.CanReconfigure`.

It intentionally does **not** implement `SysModuleAdapter`: CODESYS adapter
state and diagnostics are not the raw Rockwell `EntryStatus`, `FaultCode`,
`FaultInfo`, and `Mode` attributes required by the source-equivalent core.
This separation prevents a normalized target state from being mislabeled as
lossless Logix behavior.

The reusable target-family boundary and its separation from device profiles
are documented in
[`codesys-ethernetip-module-adapter.md`](codesys-ethernetip-module-adapter.md).
