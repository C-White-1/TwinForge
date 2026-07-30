# Executable intermediate representation

TwinForge lowers resolved controller logic into a typed, vendor-neutral
executable intermediate representation before selecting a PLCopen target.
This prevents CODESYS conventions from becoming assumptions for OpenPLC or
other IEC runtimes.

## Boundary

```text
Captured source
    |
    v
Lossless syntax
    |
    v
Resolved semantics
    |
    v
Executable IR
    |
    +--> canonical IEC Structured Text emitter
    +--> CODESYS PLCopen adapter
    +--> future OpenPLC adapter
```

The IR currently represents:

- typed references and literals;
- unary and binary expressions;
- validated member, array and dynamic-bit access;
- classified calls and target-adapter requirements;
- array-dimension queries;
- assignments and effectful calls;
- `IF` branches, `WHILE` loops and `EXIT`;
- reusable-unit parameters, local variables and routines;
- unsupported expressions and statements with their original source spans;
- lowering and interface-effect diagnostics.

The source syntax document and routine text remain unchanged. Lowering does
not authorize a target exporter to omit unsupported nodes.

## `Str_Capacity` proof

The captured Rockwell instruction:

```text
SIZE(Ref_Data, 0, Val);
```

lowers to the neutral operation:

```text
Val := array_dimension(Ref_Data, 0)
```

This is represented structurally as an assignment containing an
`IRArrayDimension`; it is not stored as generated target text.

The captured AOI declares `Val` with `Usage="Input"` even though the
implementation writes it. The IR preserves that interface and emits a
`write_to_input_parameter` diagnostic. A later target transformation must
explicitly preserve or redesign this effect instead of silently changing the
interface.

`Str_Capacity` is currently classified as a function candidate because it has
no retained local tags or lifecycle routines. This classification is an
implementation-shape recommendation, not proof that its captured interface is
already valid for every IEC target.

## Explicit interface normalization

Interface normalization is a separate, opt-in IR transformation. Its default
`preserve` policy returns the original immutable unit without changes. The
`promote_written_inputs` policy may be selected when an IEC-compatible
interface is required:

- an input proven to be an assignment target is promoted to an output;
- a function candidate requiring that multi-direction interface is promoted
  to a function block;
- each change is recorded as an IR diagnostic;
- the original captured IR and L5X source remain unchanged.

For `Str_Capacity`, this promotes `Val` to `VAR_OUTPUT` and records
`input_promoted_to_output` and `unit_promoted_to_function_block`. This is an
explicit interoperability decision, not a reinterpretation of the captured
Rockwell declaration.

## AOI execution semantics

Rockwell AOI enable behavior is applied as a separate target-neutral
transformation after interface normalization:

- `EnableOut` receives the default state of `EnableIn`;
- the primary Logic routine executes only while `EnableIn` is true;
- source logic inside the primary routine may subsequently override
  `EnableOut`;
- disabled Prescan, Postscan, and EnableInFalse flags remain captured but do
  not generate executable calls;
- an enabled lifecycle mode without a mapped captured routine makes emission
  incomplete.

For `Str_Capacity`, whose three optional lifecycle flags are false, the
transformed body is:

```iecst
EnableOut := EnableIn;
IF EnableIn THEN
    Val := array_dimension(Ref_Data, 0);
END_IF;
```

The transformation is auditable and idempotent. It records
`default_enable_out_synthesized`, `main_routine_guarded_by_enable_in`, and
`aoi_enable_semantics_applied`.

Rockwell represents optional lifecycle logic with a separate
`ScanModeRoutine` container. TwinForge captures those routines separately from
primary logic and lowers the documented names to explicit IR roles:

| Captured name | IR role |
| --- | --- |
| `Prescan` | `prescan` |
| `Postscan` | `postscan` |
| `EnableInFalse` | `enable_in_false` |

Unknown scan-mode names remain `unknown_lifecycle` and block complete
emission. An enabled EnableInFalse routine is mapped into the normal
enable-guard's false branch. Disabled lifecycle routines remain retained in
IR but are excluded from emitted normal logic.

Prescan and Postscan require target startup/shutdown semantics and therefore
remain explicit blocking requirements when enabled. Their source is never
concatenated into the cyclic function-block body.

Observed Studio 5000 v35 exports can also place a lifecycle-named routine,
such as `Prescan`, inside the ordinary `<Routines>` container. TwinForge
retains that captured container placement but assigns the execution role from
the documented routine name. It emits an informational
`lifecycle_routine_in_routines_container` diagnostic so the source-layout
variation remains visible.

For CODESYS, an explicit `FB_Init` method is the leading Prescan adapter
candidate. CODESYS calls this hook during function-block initialization and
requires the `bInitRetains` and `bInCopyCode` inputs. Its online-change
behavior is not identical to a Rockwell prescan event.

The native `11_fb_init.xml` evidence confirms that CODESYS nests an
`FB_Init` `Method` inside the function block's application-extension
`addData`. TwinForge now emits enabled captured Prescan logic there, followed
by `FB_Init := TRUE;`, and includes the mandatory Boolean inputs
`bInitRetains` and `bInCopyCode`. It deliberately does not condition the
source Prescan logic on either target input because the Rockwell source
contains no corresponding condition.

This is an explicit CODESYS adapter, not a neutral IR assumption. Cold-start,
warm-start, online-change, and Program-to-Run equivalence still require
runtime tests. Declaration initializers are not used as a general substitute
for arbitrary Prescan logic. See the official CODESYS documentation for
[`FB_Init`, `FB_Reinit`, and `FB_Exit`](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_method_fb_init_fb_reinit.html).

Wall-clock reads are also explicit neutral IR statements. The operation
records the destination and timestamp unit; it does not retain a generic
opaque `GSV` call. For the observed Rockwell
`GSV(WallClockTime, ..., CurrentValue, ...)` service, that unit is
microseconds.

The CODESYS adapter maps the operation to `SysTimeRtcHighResGet`, adds
target-only `SysTime` and `SysTypes.RTS_IEC_RESULT` state, and converts the
returned UTC milliseconds to microseconds. This preserves the source
arithmetic rather than rewriting unrelated expressions. Logic following the
read is guarded by the result code. On failure, ordinary Boolean output
parameters are forced false so stale time is not presented as a valid pulse.
The required `SysTimeRtc`, `SysTime`, and `SysTypes` libraries are emitted
only when the mapped capability is present.

Scalar AOI parameter defaults remain typed evidence in executable IR. When
the example exporter integrates a function-block instance into `PLC_PRG`, it
copies those defaults to the corresponding program-local variables. Generated
binding names use IEC-style datatype prefixes (`x`, `di`, `li`, and so on),
so a binding never relies on case alone to differ from its parameter. For
example, `Inp_Interval` is bound to `diInp_Interval`, initialized to the
captured value `1000`.

The capture tests use `tests/data/aoi/scan_mode_routines.L5X`, a fixture
derived from the structure documented in Rockwell publication
1756-RM014D-EN-P. It is labelled as specification-derived and is not presented
as a Studio 5000 export. A native exported fixture should replace or supplement
it when available.

## Target-independent rules

- Every IR node retains a source span.
- Known expression types are copied from semantic analysis.
- Unresolved references or accesses become unsupported IR expressions.
- Unknown calls are never treated as portable calls.
- A source-vendor call retains its vendor and an `adapter_required` marker.
- Rockwell output-operand instructions may lower into neutral assignments
  only through explicit, tested rules.

The first such rule is `SIZE(array, dimension, destination)`. Additional
instruction rules will be added individually with semantic and target tests.

## Canonical IEC Structured Text

The canonical IEC emitter consumes only executable IR. It renders portable
operators and control flow directly, while emitting TwinForge intrinsics for
neutral operations that require target support:

| Intrinsic | Target requirement |
| --- | --- |
| `TF_ArrayDimension(array, dimension)` | `array_dimension` |
| `TF_BitAt(value, bit)` | `dynamic_bit_access` |
| `TF_<operation>(...)` | `source_operation_adapter` |

Generic `InOut` arrays render as `ARRAY[*] OF <type>` and add the
`generic_array_interface` requirement. A CODESYS or OpenPLC adapter must map
each reported requirement or reject the output.

Without normalization, `Str_Capacity` emits:

```iecst
FUNCTION_BLOCK Str_Capacity
VAR_INPUT
    EnableIn : BOOL;
    Val : DINT;
END_VAR
VAR_OUTPUT
    EnableOut : BOOL;
END_VAR
VAR_IN_OUT
    Ref_Data : ARRAY[*] OF SINT;
END_VAR
Val := TF_ArrayDimension(Ref_Data, 0);
END_FUNCTION_BLOCK
```

The emission is intentionally marked incomplete because `Val` is a captured
input that the body writes. The use of a function block rather than the IR's
function-candidate recommendation is also reported. No target import should
be described as successful until that interface effect and both target
requirements have explicit mappings.

With `promote_written_inputs`, it emits:

```iecst
FUNCTION_BLOCK Str_Capacity
VAR_INPUT
    EnableIn : BOOL;
END_VAR
VAR_OUTPUT
    EnableOut : BOOL;
    Val : DINT;
END_VAR
VAR_IN_OUT
    Ref_Data : ARRAY[*] OF SINT;
END_VAR
Val := TF_ArrayDimension(Ref_Data, 0);
END_FUNCTION_BLOCK
```

That canonical emission is complete at the neutral IEC layer. It still
reports `array_dimension` and `generic_array_interface` requirements, which a
CODESYS or OpenPLC adapter must implement before claiming target-ready output.

## CODESYS Structured Text adapter

The CODESYS adapter consumes the same executable IR and uses documented
CODESYS constructs:

- `ARRAY[*] OF <type>` remains a variable-length `VAR_IN_OUT` array;
- a zero-based neutral `array_dimension(array, n)` becomes
  `UPPER_BOUND(array, n + 1) - LOWER_BOUND(array, n + 1) + 1`.

The `+ 1` on the dimension operand is intentional: Rockwell `SIZE` numbers its
first dimension as zero, while CODESYS identifies the first dimension as one.
Subtracting the lower bound is necessary because an IEC array does not have
to begin at index zero.

After interface and AOI execution normalization, the `Str_Capacity` body
becomes:

```iecst
EnableOut := EnableIn;
IF EnableIn THEN
    Val := ((UPPER_BOUND(Ref_Data, (0 + 1))
        - LOWER_BOUND(Ref_Data, (0 + 1))) + 1);
END_IF;
```

Both target requirements are resolved by this adapter, so the resulting
CODESYS ST emission has no unresolved requirements. The normalization
diagnostics remain attached as an audit trail.

## CODESYS PLCopen XML

`CodesysIRPLCopenExporter` packages the adapted ST and normalized interface as
a CODESYS application-extension POU. Its variable-length array representation
is based on the native CODESYS export
`reference/PLCopenXML/codesys-native/10_variable_array_size.xml`.

CODESYS represents the `VAR_IN_OUT` declaration differently from the standard
PLCopen interface lists:

```xml
<inputVars>
  <variable name="Ref_Data">
    <type>
      <pointer>
        <baseType><SINT /></baseType>
      </pointer>
    </type>
    <addData>
      <!-- CODESYS attributes retain the Inout scope, ARRAY[*] type and
           dimension count. -->
    </addData>
  </variable>
</inputVars>
```

TwinForge reproduces the native extension attributes, emits deterministic
Application and POU object IDs, and retains IR diagnostics and unresolved
requirements in `CodesysPLCopenIRResult`. CODESYS generic-array support is
claimed only for function-block `VAR_IN_OUT`; other directions remain explicit
unresolved requirements.

The PLCopen IR exporter always packages the reusable POU and can optionally
consume an explicit `CodesysProjectIntegration`. That configuration adds:

- a program POU such as `PLC_PRG`;
- a function-block instance and typed local argument variables;
- an ST function-block call with direction-correct `:=` and `=>` bindings;
- a cyclic task and scheduled `pouInstance`; and
- matching deterministic project-structure objects.

Generic arrays require an explicit fixed dimension at the call site. The
exporter does not infer an actual array length from the AOI's `ARRAY[*]`
interface.

Unsupported IR nodes emit visible `TwinForge unsupported` comments or
`TF_UNSUPPORTED()` expressions and make the result incomplete. Units with
multiple source routines also remain incomplete until their normal,
prescan/postscan, or other lifecycle roles are mapped.
