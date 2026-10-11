# -*- coding: utf-8 -*-
"""TwinForge feasibility test: a design-time drum pattern dialog in CODESYS.

Answers two questions before a real pattern editor is built:
  1. Can a CODESYS script show a Windows Forms dialog (a step x bit grid)?
  2. Can it write the resulting pattern table into the open project?

Run with a project open (any standard project; the TwinForge test project is
fine): Tools > Scripting > Execute Script File..., choose this file. Tick
some boxes, press OK. Expected: the table is printed in the Messages window
(Script category) and a global variable list TF_DrumPatternTest appears under
the application holding it. Running it again replaces the list's contents.

This runs inside CODESYS's IronPython 2.7 ScriptEngine (it uses the
`projects` object CODESYS provides), not in TwinForge's Python.
"""
from __future__ import print_function

import clr

clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
from System.Drawing import Size  # noqa: E402
from System.Windows.Forms import (  # noqa: E402
    Button, DataGridView, DataGridViewCheckBoxColumn, DialogResult, DockStyle, Form, FormStartPosition,
)

STEPS = 4
BITS = 16
GVL_NAME = "TF_DrumPatternTest"


def pattern_dialog():
    """Show the grid; return one word per step, or None if cancelled."""
    form = Form()
    form.Text = "TwinForge drum pattern (feasibility test)"
    form.Size = Size(420, 560)
    form.StartPosition = FormStartPosition.CenterScreen
    grid = DataGridView()
    grid.Dock = DockStyle.Fill
    grid.AllowUserToAddRows = False
    grid.RowHeadersWidth = 70
    for step in range(STEPS):
        column = DataGridViewCheckBoxColumn()
        column.HeaderText = "Step %d" % step
        column.Width = 70
        grid.Columns.Add(column)
    for bit in range(BITS):
        row = grid.Rows.Add()
        grid.Rows[row].HeaderCell.Value = "Bit %d" % bit
    ok = Button()
    ok.Text = "OK"
    ok.Dock = DockStyle.Bottom
    ok.DialogResult = DialogResult.OK
    form.Controls.Add(grid)
    form.Controls.Add(ok)
    form.AcceptButton = ok
    if form.ShowDialog() != DialogResult.OK:
        return None
    grid.EndEdit()  # commit the last ticked box
    words = []
    for step in range(STEPS):
        word = 0
        for bit in range(BITS):
            if grid.Rows[bit].Cells[step].Value:
                word |= 1 << bit
        words.append(word)
    return words


def declaration(words):
    """The pattern table as binary literals, bit 0 on the right."""
    lines = [
        "VAR_GLOBAL CONSTANT",
        "    (*                              bit: 1111 1100 0000 0000",
        "                                         5432 1098 7654 3210 *)",
    ]
    for step, word in enumerate(words):
        bits = format(word, "016b")
        lines.append("    DRUM_STEP%d : WORD := 2#%s_%s_%s_%s;" % (step, bits[0:4], bits[4:8], bits[8:12], bits[12:16]))
    lines.append("END_VAR")
    return "\n".join(lines)


words = pattern_dialog()
if words is None:
    print("Cancelled; nothing written.")
else:
    text = declaration(words)
    print(text)
    application = projects.primary.active_application  # noqa: F821 - provided by CODESYS
    found = application.find(GVL_NAME, False)
    gvl = found[0] if found else application.create_gvl(GVL_NAME)
    gvl.textual_declaration.replace(text)
    print("Written to %s" % GVL_NAME)
