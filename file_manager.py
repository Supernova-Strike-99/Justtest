# file_manager.py
import os
from tkinter import messagebox, Toplevel, ttk, Frame, Label
from tkinter import LEFT, RIGHT, BOTH, Y, VERTICAL, Scrollbar

class FileManager:
    def __init__(self, score_file="scores.csv", saves_dir="saves"):
        self.score_file = score_file
        self.saves_dir = saves_dir
        os.makedirs(self.saves_dir, exist_ok=True)
        self.slot_files = [os.path.join(self.saves_dir, f"slot{i}.txt") for i in range(1, 4)]

    def save_score(self, name, elapsed, rows, cols, mines, result, clicks=None, seed=None):
        seed_val = "?" if seed is None else str(seed)
        clicks_val = "?" if clicks is None else str(clicks)
        try:
            with open(self.score_file, "a") as f:
                f.write(f"{name},{elapsed},{clicks_val},{rows},{cols},{mines},{result},{seed_val}\n")
        except Exception:
            pass

    def load_scores(self):
        if not os.path.exists(self.score_file):
            return []
        out = []
        try:
            with open(self.score_file, "r") as f:
                for line in f:
                    parts = [p.strip() for p in line.strip().split(",")]
                    if len(parts) < 7:
                        continue
                    name = parts[0]
                    elapsed = parts[1] if len(parts) > 1 else "?"
                    clicks = parts[2] if len(parts) > 2 else "?"
                    rows = parts[3] if len(parts) > 3 else "?"
                    cols = parts[4] if len(parts) > 4 else "?"
                    mines = parts[5] if len(parts) > 5 else "?"
                    result = parts[6] if len(parts) > 6 else "?"
                    seed = parts[7] if len(parts) > 7 else "?"
                    out.append({
                        "name": name, "elapsed": elapsed, "clicks": clicks,
                        "rows": rows, "cols": cols, "mines": mines, "result": result, "seed": seed
                    })
        except Exception:
            return out
        return out

    def show_leaderboard(self, parent):
        """Global leaderboard: two tabs (Wins / Losses). Each tab lists one row per player
           showing the most recent entry in that category. Clicking a row opens player's full
           history filtered to that category."""
        scores = self.load_scores()
        if not scores:
            messagebox.showinfo("Leaderboard", "No scores yet — be the first loser.")
            return

        # Build maps latest by player for wins and losses (scan oldest->newest)
        latest_win = {}
        latest_loss = {}
        players = set()
        for s in scores:
            players.add(s["name"])
            if s.get("result", "").lower() == "win":
                latest_win[s["name"]] = s
            elif s.get("result", "").lower() in ("lose", "loss"):
                latest_loss[s["name"]] = s

        wins_list = list(latest_win.values())
        losses_list = list(latest_loss.values())

        # Sort by elapsed ascending (fastest first) for nicer presentation
        def timekey(e):
            t = e.get("elapsed", "?")
            return int(t) if isinstance(t, str) and t.isdigit() else (int(t) if isinstance(t, int) else 999999)

        wins_list.sort(key=timekey)
        losses_list.sort(key=timekey)

        winw = Toplevel(parent)
        winw.title("Leaderboard")
        winw.geometry("760x420")
        winw.minsize(520, 320)

        notebook = ttk.Notebook(winw)
        notebook.pack(fill=BOTH, expand=True, padx=6, pady=6)

        columns = ("player", "time", "difficulty", "clicks")
        def create_tab(title, data_list, is_win_tab):
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=title)

            tree = ttk.Treeview(frame, columns=columns, show="headings")
            tree.heading("player", text="Player")
            tree.heading("time", text="Time (s)")
            tree.heading("difficulty", text="Difficulty [rowsxcols,mines]")
            tree.heading("clicks", text="Clicks")

            tree.column("player", width=220, anchor="w")
            tree.column("time", width=80, anchor="center")
            tree.column("difficulty", width=320, anchor="center")
            tree.column("clicks", width=80, anchor="center")

            vsb = Scrollbar(frame, orient=VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=vsb.set)
            vsb.pack(side=RIGHT, fill=Y)
            tree.pack(side=LEFT, fill=BOTH, expand=True)

            # Insert a row per player (their most recent entry for this category)
            for idx, s in enumerate(data_list):
                name = s["name"]
                t = s.get("elapsed", "?")
                diff = f"[{s.get('rows','?')}x{s.get('cols','?')},{s.get('mines','?')}]"
                clicks = s.get("clicks", "?")
                iid = f"{title}_{idx}_{name}"
                tree.insert("", "end", iid=iid, values=(name, t, diff, clicks))

            # Click handler: open that player's full history filtered by category
            def on_click(event):
                row = tree.identify_row(event.y)
                if not row:
                    return
                player = tree.item(row, "values")[0]
                # Filter scores for this player and this category
                cat = "win" if is_win_tab else "lose"
                hist = [h for h in scores if h["name"] == player and h.get("result","").lower() == cat]
                if not hist:
                    messagebox.showinfo("History", f"No {cat}s found for {player}.")
                    return
                hist.sort(key=lambda h: int(h["elapsed"]) if isinstance(h.get("elapsed"), str) and h["elapsed"].isdigit() else 999999)
                hw = Toplevel(winw)
                hw.title(f"{player} — {title} history")
                hw.geometry("620x320")
                tree2 = ttk.Treeview(hw, columns=("idx", "time", "clicks", "difficulty", "seed"), show="headings")
                tree2.heading("idx", text="#")
                tree2.heading("time", text="Time(s)")
                tree2.heading("clicks", text="Clicks")
                tree2.heading("difficulty", text="Difficulty")
                tree2.heading("seed", text="Seed")
                tree2.column("idx", width=40, anchor="center")
                tree2.column("time", width=80, anchor="center")
                tree2.column("clicks", width=80, anchor="center")
                tree2.column("difficulty", width=300, anchor="w")
                tree2.column("seed", width=80, anchor="center")
                tree2.pack(fill=BOTH, expand=True, padx=8, pady=8)
                for i, h in enumerate(hist, start=1):
                    diff = f"[{h.get('rows','?')}x{h.get('cols','?')},{h.get('mines','?')}]"
                    tree2.insert("", "end", values=(i, h.get("elapsed","?"), h.get("clicks","?"), diff, h.get("seed","?")))
                hw.transient(winw); hw.grab_set(); hw.focus_force(); hw.update_idletasks()

            tree.bind("<ButtonRelease-1>", on_click)
            return tree

        create_tab("Wins", wins_list, is_win_tab=True)
        create_tab("Losses", losses_list, is_win_tab=False)

        winw.transient(parent)
        winw.grab_set()
        winw.focus_force()
        winw.update_idletasks()

    # slot operations (same as before)
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
        elapsed = int(lines[1])
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
        return {"rows": rows, "cols": cols, "mines": mines, "grid": grid, "revealed": revealed, "flagged": flagged, "elapsed": elapsed, "seed": seed}

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
            if messagebox.askyesno("Confirm", "Clear leaderboard?"):
                os.remove(self.score_file)
                messagebox.showinfo("Done", "Leaderboard cleared.")
        else:
            messagebox.showinfo("Info", "Leaderboard already empty.")
