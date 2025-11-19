# file_manager.py
import os
import json
import time
from tkinter import messagebox, Toplevel, Frame, Label, Button, PhotoImage
from tkinter import LEFT, RIGHT, BOTH, X, Y
from tkinter import ttk


class FileManager:
    def __init__(self, score_file="scores.csv", saves_dir="saves",
                 profiles_file="profiles.json",
                 logo_path="/mnt/data/8f15e2c1-1ecb-4efa-9f8b-999cb660c002.png"):

        self.score_file = score_file
        self.saves_dir = saves_dir
        self.profiles_file = profiles_file
        self.logo_path = logo_path

        self.slot_files = [
            os.path.join(self.saves_dir, f"slot{i}.txt")
            for i in range(1, 4)
        ]

        os.makedirs(self.saves_dir, exist_ok=True)

        if not os.path.exists(self.profiles_file):
            with open(self.profiles_file, "w") as f:
                json.dump([], f)

    def save_score(self, name, elapsed, rows, cols, mines, result,
                   clicks=None, seed=None):
        seed_val = seed if seed is not None else "?"
        clicks_val = clicks if clicks is not None else "?"
        with open(self.score_file, "a") as f:
            f.write(f"{name},{elapsed},{clicks_val},{rows},{cols},{mines},{result},{seed_val}\n")
        if seed is not None:
            try:
                self.save_player_profile(name, seed)
            except:
                pass

    def load_scores(self):
        if not os.path.exists(self.score_file):
            return []
        out = []
        with open(self.score_file, "r") as f:
            for line in f:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 7:
                    continue
                out.append({
                    "name": parts[0],
                    "elapsed": parts[1],
                    "clicks": parts[2],
                    "rows": parts[3],
                    "cols": parts[4],
                    "mines": parts[5],
                    "result": parts[6],
                    "seed": parts[7] if len(parts) > 7 else "?",
                })
        return out

    def _read_profiles(self):
        try:
            with open(self.profiles_file, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            return []

    def _write_profiles(self, profiles):
        try:
            with open(self.profiles_file, "w") as f:
                json.dump(profiles, f)
        except:
            pass

    def save_player_profile(self, name, seed):
        name = name.strip()
        if not name:
            return
        profiles = self._read_profiles()
        now = int(time.time())
        for p in profiles:
            if p["name"] == name:
                p["seed"] = seed
                p["last_seen"] = now
                self._write_profiles(profiles)
                return
        profiles.append({"name": name, "seed": seed, "last_seen": now})
        profiles = sorted(profiles, key=lambda x: x["last_seen"], reverse=True)[:3]
        self._write_profiles(profiles)

    def get_profiles(self):
        p = self._read_profiles()
        return sorted(p, key=lambda x: x["last_seen"], reverse=True)

    def show_personal_leaderboard(self, parent, player_name):
        scores = self.load_scores()
        if not scores:
            messagebox.showinfo("Leaderboard", "No scores yet.")
            return

        win = Toplevel(parent)
        win.title("Leaderboard")
        win.geometry("820x460")

        top = Frame(win)
        top.pack(fill=X, padx=8, pady=6)
        Label(top, text="Leaderboard", font=("Arial", 14, "bold")).pack(side=LEFT)

        try:
            if os.path.exists(self.logo_path):
                img = PhotoImage(file=self.logo_path)
                lbl = Label(top, image=img)
                lbl.image = img
                lbl.pack(side=RIGHT)
        except:
            pass

        notebook = ttk.Notebook(win)
        notebook.pack(fill=BOTH, expand=True, padx=10, pady=6)

        cols = ("idx", "player", "result", "time", "clicks", "difficulty", "seed")

        def make_tab(title):
            frame = Frame(notebook)
            notebook.add(frame, text=title)
            tree_frame = Frame(frame)
            tree_frame.pack(fill=BOTH, expand=True)
            vsb = ttk.Scrollbar(tree_frame, orient="vertical")
            tree = ttk.Treeview(tree_frame, columns=cols, show="headings", yscrollcommand=vsb.set)
            vsb.config(command=tree.yview)
            vsb.pack(side=RIGHT, fill=Y)
            tree.pack(side=LEFT, fill=BOTH, expand=True)
            tree._tab_type = title.lower()
            tree.heading("idx", text="#"); tree.heading("player", text="Player"); tree.heading("result", text="Result")
            tree.heading("time", text="Time (s)"); tree.heading("clicks", text="Clicks"); tree.heading("difficulty", text="Difficulty")
            tree.heading("seed", text="Seed")
            tree.column("idx", width=40, anchor="center"); tree.column("player", width=160, anchor="w")
            tree.column("result", width=80, anchor="center"); tree.column("time", width=80, anchor="center")
            tree.column("clicks", width=80, anchor="center"); tree.column("difficulty", width=160, anchor="center")
            tree.column("seed", width=100, anchor="center")

            def on_double(event, tv=tree):
                iid = tv.identify_row(event.y)
                if not iid:
                    return
                # robustly get player name from the 'player' column (returns string)
                player = tv.set(iid, "player")
                self._show_full_history(win, scores, player, tv._tab_type)

            tree.bind("<Double-1>", on_double)
            return tree

        tree_win = make_tab("Wins")
        tree_loss = make_tab("Losses")

        wins = [s for s in scores if (s.get("result") or "").lower() == "win"]
        losses = [s for s in scores if (s.get("result") or "").lower() in ("lose", "loss")]
        wins = list(reversed(wins)); losses = list(reversed(losses))

        def dedupe_most_recent(entries):
            seen = set(); unique = []
            for s in entries:
                pname = (s.get("name","") or "").strip().lower()
                if not pname: continue
                if pname in seen: continue
                seen.add(pname); unique.append(s)
            return unique

        unique_wins = dedupe_most_recent(wins)
        unique_losses = dedupe_most_recent(losses)

        def insert_rows(tree, data):
            for idx, s in enumerate(data, start=1):
                diff = f"[{s.get('rows','?')}x{s.get('cols','?')},{s.get('mines','?')}]"
                tree.insert("", "end", values=(idx, s.get("name","?"), s.get("result","?"),
                                               s.get("elapsed","?"), s.get("clicks","?"), diff, s.get("seed","?")))

        insert_rows(tree_win, unique_wins)
        insert_rows(tree_loss, unique_losses)

    def _show_full_history(self, parent, scores, player, mode):
        pname = str(player or "").strip().lower()
        if not pname:
            messagebox.showinfo("History", "Invalid player.")
            return

        if mode == "wins":
            hist = [x for x in scores if x.get("name","").strip().lower()==pname and (x.get("result") or "").lower()=="win"]
            title_suffix = " — Wins"
        elif mode == "losses":
            hist = [x for x in scores if x.get("name","").strip().lower()==pname and (x.get("result") or "").lower() in ("lose","loss")]
            title_suffix = " — Losses"
        else:
            hist = [x for x in scores if x.get("name","").strip().lower()==pname]
            title_suffix = " — Full History"

        if not hist:
            messagebox.showinfo("History", "No matching history for this player in this tab.")
            return

        def timekey(h):
            t = h.get("elapsed","?")
            return int(t) if str(t).isdigit() else 999999
        hist.sort(key=timekey)

        fastest_elapsed = None
        for h in hist:
            t = h.get("elapsed","?")
            if str(t).isdigit():
                val = int(t)
                if fastest_elapsed is None or val < fastest_elapsed:
                    fastest_elapsed = val

        hw = Toplevel(parent)
        hw.title(f"{player}{title_suffix}")
        hw.geometry("720x360")
        tree = ttk.Treeview(hw, columns=("idx","result","time","clicks","diff","seed"), show="headings")
        tree.heading("idx", text="#"); tree.heading("result", text="Result"); tree.heading("time", text="Time (s)")
        tree.heading("clicks", text="Clicks"); tree.heading("diff", text="Difficulty"); tree.heading("seed", text="Seed")
        tree.column("idx", width=40, anchor="center"); tree.column("result", width=80, anchor="center")
        tree.column("time", width=80, anchor="center"); tree.column("clicks", width=80, anchor="center")
        tree.column("diff", width=360, anchor="w"); tree.column("seed", width=120, anchor="center")

        tree.tag_configure("fastest", background="#e6ffe6")
        tree.pack(fill=BOTH, expand=True, padx=8, pady=8)
        for i,h in enumerate(hist, start=1):
            diff = f"[{h.get('rows','?')}x{h.get('cols','?')},{h.get('mines','?')}]"
            elapsed_val = h.get("elapsed","?")
            tag = ()
            try:
                if fastest_elapsed is not None and str(elapsed_val).isdigit() and int(elapsed_val) == fastest_elapsed:
                    tag = ("fastest",)
            except Exception:
                tag = ()
            tree.insert("", "end", values=(i, h.get("result","?"), elapsed_val, h.get("clicks","?"), diff, h.get("seed","?")), tags=tag)

        hw.transient(parent); hw.grab_set(); hw.focus_force(); hw.update_idletasks()

    # slot helpers unchanged
    def write_slot(self, slot, board_obj, elapsed):
        path = self.slot_files[slot - 1]
        seed_val = board_obj.seed if board_obj.seed is not None else 0
        with open(path, "w") as f:
            f.write(f"{board_obj.rows} {board_obj.cols} {board_obj.mines}\n")
            f.write(f"{int(elapsed)}\n")
            f.write(f"{int(seed_val)}\n")
            for row in board_obj.grid:
                f.write("".join(row) + "\n")
            for row in board_obj.revealed:
                f.write("".join("1" if x else "0" for x in row) + "\n")
            flags = ";".join(f"{r},{c}" for (r, c) in board_obj.flagged)
            f.write(flags + "\n")

    def read_slot(self, slot):
        path = self.slot_files[slot - 1]
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            lines = [l.rstrip("\n") for l in f.readlines()]
        if len(lines) < 3:
            return None
        header = lines[0].split()
        if len(header) != 3 or not all(h.isdigit() for h in header):
            return None
        rows, cols, mines = map(int, header)
        if not lines[1].lstrip("-").isdigit():
            return None
        elapsed = int(lines[1])
        if not lines[2].lstrip("-").isdigit():
            return None
        seed = int(lines[2])
        if len(lines) < 3 + rows + rows:
            return None
        grid = [list(lines[3 + r]) for r in range(rows)]
        rev_start = 3 + rows
        revealed = [[c == "1" for c in lines[rev_start + r]] for r in range(rows)]
        flagged_line = lines[rev_start + rows] if len(lines) > rev_start + rows else ""
        flagged = set()
        if flagged_line:
            for pair in flagged_line.split(";"):
                if "," in pair:
                    pr, pc = pair.split(",")
                    if pr.lstrip("-").isdigit() and pc.lstrip("-").isdigit():
                        flagged.add((int(pr), int(pc)))
        return {
            "rows": rows,
            "cols": cols,
            "mines": mines,
            "grid": grid,
            "revealed": revealed,
            "flagged": flagged,
            "elapsed": elapsed,
            "seed": seed
        }

    def slot_exists(self, slot):
        return os.path.exists(self.slot_files[slot - 1])

    def delete_slot_file(self, slot):
        path = self.slot_files[slot - 1]
        if os.path.exists(path):
            os.remove(path)

    def delete_all_slots(self):
        for path in self.slot_files:
            if os.path.exists(path):
                os.remove(path)

    def clear_scores(self):
        if os.path.exists(self.score_file):
            if messagebox.askyesno("Confirm", "Clear ALL scores?"):
                os.remove(self.score_file)
                messagebox.showinfo("Done", "Scores deleted.")
        else:
            messagebox.showinfo("Info", "Leaderboard already empty.")
