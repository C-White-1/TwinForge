# -*- coding: utf-8 -*-
"""TwinForge drum pattern editor for CODESYS: the Drum Assistant's equivalent.

Edits the pattern of a TF_MEBasic_Drum (library TwinForge_MEBasic) at
design time: a grid of steps x control bits, like Machine Expert - Basic's
Drum Assistant. The pattern is kept in a global variable list (default
TF_DrumPatterns) as a marked block per drum:

    // TwinForge drum pattern DR0: begin
    // B0: xLamp0
    DR0_NSTEPS : INT := 4;
    DR0_PATTERN : ARRAY[0..7] OF WORD := [
        2#0000_0000_0000_0000,  // step 0
        2#0000_0000_0000_0011,  // step 1
        ...
    ];
    // TwinForge drum pattern DR0: end

Run again for the same drum to edit it: the block is read back and replaced;
everything else in the list is left as it is. The Messages window shows the
drum's declaration, configured like the Drum Assistant's (library 0.3.0):

    DR0 : TF_MEBasic_Drum(NSTEPS_INIT := TF_DrumPatterns.DR0_NSTEPS,
        PATTERN_INIT := TF_DrumPatterns.DR0_PATTERN,
        B0 := xLamp0, ..., B15 := xSpare);

and its call, `DR0(RESET := ..., U := ...);`. The constants are named with
the list in front, as CODESYS creates lists qualified_only.

Run with a project open: Tools > Scripting > Execute Script File... This
file runs inside CODESYS's IronPython 2.7 ScriptEngine. The text functions
above `main` are plain Python, tested by TwinForge
(tests/test_codesys_drum_pattern_editor.py); keep them Python 2.7 compatible.
"""
from __future__ import print_function

import re

MAX_STEPS = 8
BITS = 16
DEFAULT_GVL = "TF_DrumPatterns"
DEFAULT_DRUM = "DR0"
BEGIN = "// TwinForge drum pattern %s: begin"
END = "// TwinForge drum pattern %s: end"
INDENT = "    "
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def valid_drum_name(name):
    """A drum name prefixes IEC identifiers, so it must be one itself."""
    return bool(_IDENTIFIER.match(name)) and "__" not in name and not name.endswith("_")


def binary_literal(word):
    bits = format(word, "016b")
    return "2#%s_%s_%s_%s" % (bits[0:4], bits[4:8], bits[8:12], bits[12:16])


def format_block(drum, steps, words, names):
    """The marked declaration block for one drum (lines, without indent)."""
    lines = [BEGIN % drum]
    for bit in range(BITS):
        if names[bit].strip():
            lines.append("// B%d: %s" % (bit, names[bit].strip()))
    lines.append("%s_NSTEPS : INT := %d;" % (drum, steps))
    lines.append("%s_PATTERN : ARRAY[0..%d] OF WORD := [" % (drum, MAX_STEPS - 1))
    for step in range(MAX_STEPS):
        comma = "," if step < MAX_STEPS - 1 else ""
        note = "" if step < steps else " (unused)"
        lines.append("%s%s%s  // step %d%s" % (INDENT, binary_literal(words[step]), comma, step, note))
    lines.append("];")
    lines.append(END % drum)
    return lines


def _block_span(lines, drum):
    """(first, last) line indexes of the drum's block, or None."""
    begin, end = BEGIN % drum, END % drum
    first = last = None
    for index, line in enumerate(lines):
        if line.strip() == begin:
            first = index
        elif line.strip() == end and first is not None:
            last = index
            break
    return (first, last) if first is not None and last is not None else None


def parse_block(declaration, drum):
    """(steps, words, names) from the drum's block in a declaration, or None."""
    lines = declaration.splitlines()
    span = _block_span(lines, drum)
    if span is None:
        return None
    block = lines[span[0]:span[1] + 1]
    names = [""] * BITS
    steps = MAX_STEPS
    words = []
    for line in block:
        text = line.strip()
        named = re.match(r"^// B(\d+): (.*)$", text)
        if named and int(named.group(1)) < BITS:
            names[int(named.group(1))] = named.group(2).strip()
            continue
        counted = re.match(r"^%s_NSTEPS\s*:\s*INT\s*:=\s*(\d+)\s*;" % re.escape(drum), text)
        if counted:
            steps = max(1, min(MAX_STEPS, int(counted.group(1))))
            continue
        literal = re.match(r"^2#([01_]+)", text)
        if literal:
            words.append(int(literal.group(1).replace("_", ""), 2))
    words = (words + [0] * MAX_STEPS)[:MAX_STEPS]
    return steps, words, names


def merge_block(declaration, drum, block):
    """The declaration with the drum's block replaced, or added.

    A block already there is replaced in place. Otherwise it goes before the
    END_VAR of the first VAR_GLOBAL CONSTANT section, or in a new section.
    """
    lines = declaration.splitlines()
    indented = [INDENT + line for line in block]
    span = _block_span(lines, drum)
    if span is not None:
        lines[span[0]:span[1] + 1] = indented
        return "\n".join(lines) + "\n"
    for index, line in enumerate(lines):
        if re.match(r"^\s*VAR_GLOBAL\s+CONSTANT\b", line, re.IGNORECASE):
            for end in range(index + 1, len(lines)):
                if re.match(r"^\s*END_VAR\b", lines[end], re.IGNORECASE):
                    lines[end:end] = indented
                    return "\n".join(lines) + "\n"
    section = ["VAR_GLOBAL CONSTANT"] + indented + ["END_VAR"]
    if declaration.strip():
        return declaration.rstrip("\n") + "\n\n" + "\n".join(section) + "\n"
    return "\n".join(section) + "\n"


def usage(drum, names, gvl=DEFAULT_GVL):
    """The drum's declaration and call, for the Messages window.

    The drum (library 0.3.0) is configured in its declaration, as the Drum
    Assistant configures Basic's: step count, pattern, and the output each
    bit drives (unused bits share xSpare). The constants are named with
    their list in front: CODESYS creates a new global variable list with
    {attribute 'qualified_only'}, which makes that form required (and it
    works without the attribute too).
    """
    bound = ["B%d := %s" % (bit, names[bit].strip() or "xSpare") for bit in range(BITS)]
    outputs = ",\n    ".join(", ".join(bound[i:i + 4]) for i in range(0, BITS, 4))
    return ("Declaration:\n%s : TF_MEBasic_Drum(NSTEPS_INIT := %s.%s_NSTEPS, PATTERN_INIT := %s.%s_PATTERN,\n"
            "    %s);\nCall:\n%s(RESET := ..., U := ...);" % (drum, gvl, drum, gvl, drum, outputs, drum))


# --- CODESYS dialog (runs only inside CODESYS) ----------------------------------

def main():  # pragma: no cover - needs CODESYS
    import clr
    clr.AddReference("System.Windows.Forms")
    clr.AddReference("System.Drawing")
    from System.Drawing import Color, Size
    from System.Windows.Forms import (
        Button, DataGridView, DataGridViewCheckBoxColumn, DataGridViewTextBoxColumn,
        DialogResult, DockStyle, FlowLayoutPanel, Form, FormStartPosition, Label, MessageBox, NumericUpDown,
        TextBox,
    )

    application = projects.primary.active_application  # noqa: F821 - provided by CODESYS

    def find_gvl(name):
        found = application.find(name, False)
        return found[0] if found else None

    form = Form()
    form.Text = "TwinForge drum pattern editor"
    form.Size = Size(860, 640)
    form.StartPosition = FormStartPosition.CenterScreen

    top = FlowLayoutPanel()
    top.Dock = DockStyle.Top
    top.Height = 40
    gvl_box = TextBox()
    gvl_box.Text = DEFAULT_GVL
    gvl_box.Width = 160
    drum_box = TextBox()
    drum_box.Text = DEFAULT_DRUM
    drum_box.Width = 100
    load = Button()
    load.Text = "Load"
    steps_box = NumericUpDown()
    steps_box.Minimum = 1
    steps_box.Maximum = MAX_STEPS
    steps_box.Value = 4
    steps_box.Width = 50
    for control, caption in ((gvl_box, "Global variable list:"), (drum_box, "Drum:"), (load, None),
                             (steps_box, "Number of steps:")):
        if caption:
            label = Label()
            label.Text = caption
            label.AutoSize = True
            top.Controls.Add(label)
        top.Controls.Add(control)

    grid = DataGridView()
    grid.Dock = DockStyle.Fill
    grid.AllowUserToAddRows = False
    grid.RowHeadersWidth = 60
    output = DataGridViewTextBoxColumn()
    output.HeaderText = "Output (variable)"
    output.Width = 180
    grid.Columns.Add(output)
    for step in range(MAX_STEPS):
        column = DataGridViewCheckBoxColumn()
        column.HeaderText = "Step %d" % step
        column.Width = 62
        grid.Columns.Add(column)
    for bit in range(BITS):
        row = grid.Rows.Add()
        grid.Rows[row].HeaderCell.Value = "B%d" % bit

    def show_steps(sender=None, args=None):
        steps = int(steps_box.Value)
        for step in range(MAX_STEPS):
            column = grid.Columns[step + 1]
            column.ReadOnly = step >= steps
            column.DefaultCellStyle.BackColor = Color.LightGray if step >= steps else Color.White

    def load_pattern(sender=None, args=None):
        gvl = find_gvl(gvl_box.Text.strip())
        parsed = parse_block(gvl.textual_declaration.text, drum_box.Text.strip()) if gvl else None
        steps, words, names = parsed if parsed else (4, [0] * MAX_STEPS, [""] * BITS)
        steps_box.Value = steps
        for bit in range(BITS):
            grid.Rows[bit].Cells[0].Value = names[bit]
            for step in range(MAX_STEPS):
                grid.Rows[bit].Cells[step + 1].Value = bool(words[step] >> bit & 1)
        show_steps()
        form.Text = "TwinForge drum pattern editor - %s (%s)" % (
            drum_box.Text.strip(), "loaded" if parsed else "new")

    steps_box.ValueChanged += show_steps
    load.Click += load_pattern

    buttons = FlowLayoutPanel()
    buttons.Dock = DockStyle.Bottom
    buttons.Height = 40
    ok = Button()
    ok.Text = "Write to project"
    ok.Width = 140
    ok.DialogResult = DialogResult.OK
    cancel = Button()
    cancel.Text = "Cancel"
    cancel.DialogResult = DialogResult.Cancel
    buttons.Controls.Add(ok)
    buttons.Controls.Add(cancel)
    form.AcceptButton = ok
    form.CancelButton = cancel
    form.Controls.Add(grid)
    form.Controls.Add(top)
    form.Controls.Add(buttons)
    load_pattern()

    while True:
        if form.ShowDialog() != DialogResult.OK:
            print("Cancelled; nothing written.")
            return
        drum = drum_box.Text.strip()
        if valid_drum_name(drum):
            break
        MessageBox.Show("'%s' is not a usable name: letters, digits and single underscores, "
                        "not starting with a digit." % drum, form.Text)
    grid.EndEdit()
    steps = int(steps_box.Value)
    names = [(grid.Rows[bit].Cells[0].Value or "").strip() for bit in range(BITS)]
    words = []
    for step in range(MAX_STEPS):
        word = 0
        if step < steps:
            for bit in range(BITS):
                if grid.Rows[bit].Cells[step + 1].Value:
                    word |= 1 << bit
        words.append(word)
    gvl_name = gvl_box.Text.strip()
    gvl = find_gvl(gvl_name) or application.create_gvl(gvl_name)
    gvl.textual_declaration.replace(merge_block(gvl.textual_declaration.text, drum,
                                                format_block(drum, steps, words, names)))
    print("Wrote drum pattern %s to %s. Wire the drum:" % (drum, gvl_name))
    print(usage(drum, names, gvl_name))


try:
    projects  # noqa: B018, F821 - defined only inside CODESYS
except NameError:
    pass  # imported outside CODESYS (TwinForge's tests): no dialog
else:
    main()
