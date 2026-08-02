"""Left-hand tree-outline sidebar for the Focus Tree screen."""

from tkinter import ttk

from app import focus_tree_theme as ft


class FocusTreeSidebar(ttk.Frame):
    """Tree outline presentation and hierarchy rendering."""

    def __init__(self, parent, *, on_select):
        super().__init__(parent, width=226, style="FocusTree.Sidebar.TFrame")
        self.pack_propagate(False)

        header = ttk.Frame(self, style="FocusTree.Panel.TFrame", padding=(12, 9, 12, 7))
        header.pack(fill="x")
        ttk.Label(header, text="TREE OUTLINE", style="FocusTree.Eyebrow.TLabel").pack(side="left")
        self.count_label = ttk.Label(header, text="", style="FocusTree.ToolbarMuted.TLabel")
        self.count_label.pack(side="right")
        ttk.Frame(self, style="FocusTree.Sash.TFrame", height=1).pack(fill="x")

        outline_wrap = ttk.Frame(self, style="FocusTree.Sidebar.TFrame", padding=(6, 7))
        outline_wrap.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(outline_wrap, show="tree", selectmode="browse", style="FocusTree.Treeview")
        scrollbar = ttk.Scrollbar(outline_wrap, orient="vertical", command=self.tree.yview,
                                  style="FocusTree.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.tag_configure("sel", foreground=ft.ACCENT_HI)
        self.tree.bind("<<TreeviewSelect>>", on_select)

    def render(self, focuses, by_id, selected_id):
        """Render focus prerequisites as a navigable hierarchy."""
        tree = self.tree
        expanded = set()

        def remember_expanded(parent_iid=""):
            for child_iid in tree.get_children(parent_iid):
                if tree.item(child_iid, "open"):
                    expanded.add(child_iid)
                remember_expanded(child_iid)

        remember_expanded()
        tree.delete(*tree.get_children())
        children = {}
        roots = []
        unresolved = 0
        for focus in focuses:
            prerequisites = focus.get("prerequisite", [])
            parent = next(
                (item for item in prerequisites if item in by_id and item != focus["id"]), None
            )
            if parent:
                children.setdefault(parent, []).append(focus["id"])
            else:
                roots.append(focus["id"])
            unresolved += sum(1 for item in prerequisites if item not in by_id)

        def insert(parent_iid, focus_id, seen):
            if focus_id in seen or tree.exists(focus_id):
                return
            seen = seen | {focus_id}
            tags = ("sel",) if focus_id == selected_id else ()
            tree.insert(
                parent_iid, "end", iid=focus_id, text=focus_id, tags=tags,
                open=focus_id in expanded,
            )
            for child in sorted(children.get(focus_id, [])):
                insert(focus_id, child, seen)

        for focus_id in sorted(roots):
            insert("", focus_id, set())
        for focus in focuses:
            insert("", focus["id"], set())
        self.count_label.config(
            text=f"{unresolved} unresolved prereq(s)" if unresolved else f"{len(focuses)} focuses"
        )

    def selected_focus_id(self):
        selected = self.tree.selection()
        return selected[0] if selected else None
