"""AI Weight wizard: build an `ai_will_do` / `ai_chance` block - how eager
the AI is to take this focus/decision/option - without memorising the
factor-times-modifier-stack shape by hand.

The block has one flat shape everywhere it appears (focuses, decisions,
event options): a base `factor`, plus any number of conditional `modifier`
blocks that multiply it. This wizard only ever appends a base factor or one
modifier at a time into the target textbox, the same incremental pattern
`EffectWizard` already uses for effects/triggers - so it composes with
whatever the user already typed by hand.
"""

import tkinter as tk
from tkinter import ttk

# (label, trigger key, placeholder) - the handful of conditions that show up
# constantly in real ai_will_do stacks
COMMON_CONDITIONS = [
    ("Country has completed a focus", "has_completed_focus", "OTHER_FOCUS_ID"),
    ("Country has an idea/spirit", "has_idea", "some_idea"),
    ("Country is this tag", "tag", "TAG"),
    ("Is not this tag", "NOT = { tag", "TAG"),
    ("Date is at least", "date", "1939.1.1"),
    ("War is ongoing", "has_war", "yes"),
    ("Political power available", "has_political_power", "150"),
    ("Random chance (num_of_dice-style)", "modifier_num", ""),
]


class AIWizard(tk.Toplevel):
    """Appends into `target_text` (a tk.Text). No return value - same
    incremental-insert pattern as EffectWizard, so it can be reopened
    repeatedly while building up one stack."""

    def __init__(self, master, target_text):
        super().__init__(master)
        self.title("AI weight")
        self.resizable(False, False)
        self.target = target_text
        self._build()
        self.grab_set()

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        base = ttk.LabelFrame(self, text="Base weight", padding=10)
        base.pack(fill="x", **pad)
        ttk.Label(base, text="How eager the AI is with no conditions met (10 = neutral).").pack(anchor="w")
        row = ttk.Frame(base)
        row.pack(fill="x", pady=(6, 0))
        self.factor_var = tk.StringVar(value="10")
        ttk.Entry(row, textvariable=self.factor_var, width=8).pack(side="left")
        ttk.Button(row, text="Insert Base Factor", command=self._insert_factor).pack(side="left", padx=8)

        cond = ttk.LabelFrame(self, text="Conditional modifier", padding=10)
        cond.pack(fill="x", **pad)
        ttk.Label(cond, text="Multiplies the base factor only while this condition holds.").pack(anchor="w")

        grid = ttk.Frame(cond)
        grid.pack(fill="x", pady=(6, 0))
        ttk.Label(grid, text="When").grid(row=0, column=0, sticky="w")
        self.cond_var = tk.StringVar(value=COMMON_CONDITIONS[0][0])
        combo = ttk.Combobox(grid, textvariable=self.cond_var, state="readonly", width=32,
                             values=[c[0] for c in COMMON_CONDITIONS])
        combo.grid(row=0, column=1, padx=6)
        combo.bind("<<ComboboxSelected>>", lambda e: self._sync_placeholder())

        ttk.Label(grid, text="Value").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.value_var = tk.StringVar(value=COMMON_CONDITIONS[0][2])
        ttk.Entry(grid, textvariable=self.value_var, width=32).grid(row=1, column=1, padx=6, pady=(6, 0))

        ttk.Label(grid, text="Multiply factor by").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.mult_var = tk.StringVar(value="2")
        ttk.Entry(grid, textvariable=self.mult_var, width=10).grid(row=2, column=1, sticky="w", padx=6, pady=(6, 0))

        ttk.Button(cond, text="Insert Modifier", command=self._insert_modifier).pack(anchor="w", pady=(8, 0))

        ttk.Button(self, text="Close", command=self.destroy).pack(pady=(0, 10))

    def _sync_placeholder(self):
        for label, _, placeholder in COMMON_CONDITIONS:
            if label == self.cond_var.get():
                self.value_var.set(placeholder)
                return

    def _insert(self, text):
        self.target.insert("end", ("\n" if self.target.get("1.0", "end-1c").strip() else "") + text + "\n")

    def _insert_factor(self):
        factor = self.factor_var.get().strip() or "10"
        self._insert(f"factor = {factor}")

    def _insert_modifier(self):
        key = next((k for label, k, _ in COMMON_CONDITIONS if label == self.cond_var.get()), "tag")
        value = self.value_var.get().strip()
        mult = self.mult_var.get().strip() or "2"

        if key == "modifier_num":
            trigger = f"num_of_dice = 100\n\t\trandom_chance = {{\n\t\t\tchance = {value or '50'}\n\t\t}}"
        elif key.startswith("NOT ="):
            trigger = f"NOT = {{ tag = {value} }}"
        else:
            trigger = f"{key} = {value}"

        block = "modifier = {\n\t\tfactor = " + mult + "\n\t\t" + trigger + "\n\t}"
        self._insert(block)
