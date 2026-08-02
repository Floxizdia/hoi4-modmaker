"""Music tab: turn a pile of mp3s into a working in-game radio station.

HOI4 wants three things that have to agree with each other exactly, which
is where hand-written music mods usually break:

  music/<station>.asset  declares each song id and the file it plays
  music/<station>.txt    the station, listing which song ids belong to it
  localisation/*.yml     the display names for the station and every song

So this tab keeps one list of songs and writes all three from it, and it
copies the mp3s into the mod itself - a station pointing at files still
sitting in someone's Downloads folder works on their machine and nowhere
else, which is the classic "works for me" music mod bug.
"""

import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app.state import state
from app import mod_export
from app import theme, ui_kit

SAFE_ID = re.compile(r"[^A-Za-z0-9_]+")


def song_id(station, filename):
    """A script id derived from the file name, prefixed by the station so two
    stations can both contain a song called 'march.mp3'."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    return SAFE_ID.sub("_", f"{station}_{stem}").strip("_").lower()


def write_station(mod_root, station, songs, record=None):
    """`songs` is [{path, title, volume}]. Returns the list of files written."""
    station_id = SAFE_ID.sub("_", station).strip("_") or "my_station"
    music_dir = os.path.join(mod_root, "music")
    os.makedirs(music_dir, exist_ok=True)

    written = []
    asset_lines = []
    station_lines = [f'music_station = "{station_id}"', ""]
    loc = {station_id: station}

    for song in songs:
        src = song["path"]
        # spaces and punctuation in the file name make the asset silently fail
        # to load in game, so the copy lands under a sanitised name
        stem, ext = os.path.splitext(os.path.basename(src))
        dest = os.path.join(music_dir, SAFE_ID.sub("_", stem).strip("_") + ext.lower())
        if os.path.abspath(src) != os.path.abspath(dest):
            shutil.copy2(src, dest)
            written.append(dest)
        sid = song_id(station_id, src)
        volume = song.get("volume", "0.65")
        asset_lines.append(
            "music = {\n"
            f'\tname = "{sid}"\n'
            f'\tfile = "{os.path.basename(dest)}"\n'
            f"\tvolume = {volume}\n"
            "}\n"
        )
        station_lines.append(
            "music = {\n"
            f'\tsong = "{sid}"\n'
            "\tchance = {\n\t\tmodifier = {\n\t\t\tfactor = 1\n\t\t}\n\t}\n"
            "}\n"
        )
        loc[sid] = song["title"]

    asset_path = os.path.join(music_dir, f"{station_id}.asset")
    with open(asset_path, "w", encoding="utf-8") as f:
        f.write("\n".join(asset_lines))
    written.append(asset_path)

    txt_path = os.path.join(music_dir, f"{station_id}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(station_lines))
    written.append(txt_path)

    loc_dir = os.path.join(mod_root, "localisation", "english")
    os.makedirs(loc_dir, exist_ok=True)
    loc_path = os.path.join(loc_dir, f"{station_id}_l_english.yml")
    with open(loc_path, "w", encoding="utf-8-sig") as f:
        f.write("l_english:\n")
        for key, text in loc.items():
            f.write(f' {key}:0 "{text}"\n')
    written.append(loc_path)

    if record:
        record(written)
    return written


class MusicTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.songs = []
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Music",
            "Add music tracks to the mod's playlist (the .asset/.txt entries the game reads) without hand-editing the music definition files.", help_key="music")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Station name", style="Gold.TLabel").pack(side="left")
        self.station_var = tk.StringVar(value="My Radio")
        ttk.Entry(top, textvariable=self.station_var, width=28).pack(side="left", padx=6)
        ttk.Button(top, text="Add mp3 files...", command=self._add_files).pack(side="left")
        ttk.Button(top, text="Remove selected", command=self._remove).pack(side="left", padx=6)
        ttk.Button(top, text="Create Station", style="Accent.TButton",
                   command=self._create).pack(side="left")

        ttk.Label(
            self,
            text="The mp3s are copied into the mod's music folder, so the station keeps working "
                 "on anyone else's machine. Double-click a song to rename it — that name is what "
                 "players see in the music player.",
            style="Muted.TLabel", wraplength=980, justify="left",
        ).pack(fill="x", pady=(8, 4))

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, pady=6)
        self.tree = ttk.Treeview(frame, columns=("title", "volume", "file"), show="headings")
        for col, label, width in (("title", "Title in game", 300),
                                  ("volume", "Volume", 80),
                                  ("file", "File", 420)):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width)
        bar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.tree.bind("<Double-Button-1>", self._rename)

        self.status = ttk.Label(self, text="", style="Status.TLabel", wraplength=980, justify="left")
        self.status.pack(fill="x")

        self.on_mod_changed()

    # ---- lifecycle ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")

    # ---- song list ----

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i, song in enumerate(self.songs):
            self.tree.insert("", "end", iid=str(i),
                             values=(song["title"], song["volume"], song["path"]))

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Pick the songs for this station",
            filetypes=[("Music", "*.mp3 *.ogg *.wav"), ("All files", "*.*")],
        )
        for path in paths:
            title = os.path.splitext(os.path.basename(path))[0].replace("_", " ")
            self.songs.append({"path": path, "title": title, "volume": "0.65"})
        self._refresh()
        self.status.config(text=f"{len(self.songs)} song(s) queued.")

    def _remove(self):
        for iid in sorted(self.tree.selection(), key=int, reverse=True):
            del self.songs[int(iid)]
        self._refresh()

    def _rename(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        song = self.songs[int(iid)]
        column = self.tree.identify_column(event.x)
        field = "volume" if column == "#2" else "title"
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit {field}")
        dialog.resizable(False, False)
        var = tk.StringVar(value=song[field])
        ttk.Label(dialog, text=f"{field.title()}:").pack(side="left", padx=8, pady=10)
        entry = ttk.Entry(dialog, textvariable=var, width=34)
        entry.pack(side="left", pady=10)
        entry.focus_set()

        def commit():
            song[field] = var.get().strip() or song[field]
            self._refresh()
            dialog.destroy()

        ttk.Button(dialog, text="OK", command=commit).pack(side="left", padx=8)
        entry.bind("<Return>", lambda e: commit())
        dialog.grab_set()

    # ---- writing ----

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        if not self.songs:
            messagebox.showerror("No songs", "Add at least one mp3 to the station.")
            return
        station = self.station_var.get().strip()
        if not station:
            messagebox.showerror("No name", "Give the station a name.")
            return
        try:
            written = write_station(
                state.mod_root, station, self.songs,
                record=lambda paths: mod_export.record_created(state.mod_root, paths),
            )
        except OSError as exc:
            messagebox.showerror("Write failed", str(exc))
            return
        for song in self.songs:
            state.add_loc(song_id(SAFE_ID.sub("_", station).strip("_"), song["path"]), song["title"])
        self.status.config(
            text=f"Station '{station}' created — {len(written)} files written into music/ and "
                 "localisation/english. Launch the game and pick it in the music player."
        )
