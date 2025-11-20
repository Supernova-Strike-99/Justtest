# main.py
import tkinter as tk
from tkinter import messagebox
import sys

from board import Board
from game_logic import Game
from file_manager import FileManager

DEFAULT_ROWS, DEFAULT_COLS, DEFAULT_MINES = 9, 9, 15
PRESETS = {"Easy": (9, 9, 10), "Normal": (16, 16, 40), "Hard": (16, 30, 99)}


class BoardUI:
    def __init__(self, root, player_name_cb):
        self.root = root
        self.player_name_cb = player_name_cb
        self.btns = {}
        self._timer_job = None
        self._elapsed_fn = None
        self._cell_font = ("Helvetica", 12, "bold")
        self.num_color = {
            "1": "#0000FF", "2": "#008000", "3": "#FF0000",
            "4": "#000080", "5": "#800000", "6": "#008B8B",
            "7": "#000000", "8": "#808080"
        }

    def build(self, rows, cols, mines):
        self.rows, self.cols, self.mines = rows, cols, mines
        for w in list(self.root.grid_slaves()):
            w.grid_forget()

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)

        hdr = tk.Frame(self.root)
        hdr.grid(row=0, column=0, pady=(6, 2))
        stats_font = ("Arial", 12, "bold")
        self.lbl_time = tk.Label(hdr, text="Time: 0s", font=stats_font)
        self.lbl_time.pack(side="left", padx=(4, 8))
        self.lbl_flags = tk.Label(hdr, text=f"Flags: 0/{mines}", font=stats_font)
        self.lbl_flags.pack(side="left", padx=(0, 8))
        self.lbl_clicks = tk.Label(hdr, text="Clicks: 0", font=stats_font)
        self.lbl_clicks.pack(side="left", padx=(0, 4))

        center = tk.Frame(self.root)
        center.grid(row=1, column=0)
        holder = tk.Frame(center)
        holder.grid(row=0, column=0)

        gridf = tk.Frame(holder)
        gridf.grid(row=0, column=0)
        self.btns = {}

        gap = 1
        for r in range(rows):
            gridf.rowconfigure(r, weight=0)
            for c in range(cols):
                gridf.columnconfigure(c, weight=0)
                b = tk.Button(
                    gridf,
                    text="",
                    width=2,
                    height=1,
                    relief="raised",
                    bd=2,
                    bg="#e9e9e9",
                    activebackground="#e9e9e9",
                    font=self._cell_font
                )
                b.grid(row=r, column=c, padx=gap, pady=gap, ipadx=0, ipady=0)
                b.bind("<Button-1>", lambda ev, rr=r, cc=c: self._on_left(rr, cc))
                b.bind("<Button-3>", lambda ev, rr=r, cc=c: self._on_right(rr, cc))
                b.bind("<Button-2>", lambda ev, rr=r, cc=c: self._on_middle(rr, cc))
                b.bind("<Control-Button-1>", lambda ev, rr=r, cc=c: self._on_right(rr, cc))
                b.config(disabledforeground="black")
                self.btns[(r, c)] = b

        ctrl = tk.Frame(self.root)
        ctrl.grid(row=2, column=0, pady=(6, 6))
        tk.Button(ctrl, text="Save", width=10, command=lambda: self._on_save()).pack(side="left", padx=6)

    def bind(self, game):
        self._game = game

    def get_player_name(self):
        return self.player_name_cb()

    def _on_left(self, r, c):
        if hasattr(self, "_game"): self._game.on_left(r, c)

    def _on_right(self, r, c):
        if hasattr(self, "_game"): self._game.on_right(r, c)

    def _on_middle(self, r, c):
        if hasattr(self, "_game"): self._game.on_middle(r, c)

    def reveal_cell(self, r, c, val):
        b = self.btns.get((r, c))
        if not b: return
        b.config(relief="sunken", state="disabled")
        if val == "M":
            b.config(text="M", fg="black", bg="#ff4d4d", disabledforeground="black")
        elif val == "0":
            b.config(text="", bg="#dff7f9")
        else:
            color = self.num_color.get(str(val), "black")
            b.config(text=str(val), fg=color, disabledforeground=color, bg="#dff7f9")

    def reveal_mine(self, r, c):
        self.reveal_cell(r, c, "M")

    def set_flag(self, r, c, flagged):
        b = self.btns.get((r, c))
        if not b: return
        if flagged:
            b.config(text="F", fg="#C00000", bg="#FFF3D9", state="normal")
        else:
            b.config(text="", fg="black", bg="#e9e9e9", state="normal")

    def update_counters(self, flagged_count, mines):
        self.lbl_flags.config(text=f"Flags: {flagged_count}/{mines}")

    def start_timer(self, elapsed_fn):
        self._elapsed_fn = elapsed_fn
        self._tick()

    def _tick(self):
        if not self._elapsed_fn:
            return
        self.lbl_time.config(text=f"Time: {self._elapsed_fn()}s")
        self._timer_job = self.root.after(1000, self._tick)

    def set_timer(self, val):
        self.lbl_time.config(text=f"Time: {int(val)}s")

    def set_clicks(self, n):
        self.lbl_clicks.config(text=f"Clicks: {n}")

    def close(self):
        try:
            if getattr(self, "_timer_job", None):
                self.root.after_cancel(self._timer_job)
            self.root.destroy()
        except Exception:
            pass

    def _on_save(self):
        if hasattr(self, "_game"):
            self._game.save_prompt()


# ---------- App flow ----------
def start_game(rows, cols, mines, name, fm, slot_data=None, slot_index=None):
    """
    slot_index: optional int 1..3 — if provided, the game is loaded from that slot and the
                slot file will be deleted automatically when the user finishes the game.
    """
    game_root = tk.Tk()
    game_root.title("Minesweeper")
    game_root.resizable(False, False)

    ui = BoardUI(game_root, lambda: name)

    if slot_data is None:
        board = Board(rows, cols, mines)
    else:
        board = Board(
            slot_data["rows"],
            slot_data["cols"],
            slot_data["mines"],
            seed=slot_data.get("seed"),
            grid=slot_data.get("grid"),
            revealed=slot_data.get("revealed"),
            flagged=slot_data.get("flagged")
        )

    def post_game_cb(result, elapsed, clicks, _unused):
        e3bv = board.compute_e3bv(first_click=getattr(game, "first_click", None))
        title = "Victory!" if result == "win" else "Game Over"
        msg = f"{'You won!' if result == 'win' else 'You lost!'}\nTime: {elapsed}s\nClicks: {clicks}\ne3BV: {e3bv}\n\nGo to main menu? (Yes → main menu, No → exit)"
        res = messagebox.askyesno(title, msg, parent=game_root)
        try:
            game_root.destroy()
        except Exception:
            pass
        if res:
            main_menu(prefill_name=name)
        else:
            sys.exit(0)

    game = Game(board, fm, ui, post_game_cb)

    # If game loaded from a slot, mark it so it can be cleared on finish
    if slot_index is not None:
        game.current_save_slot = slot_index

    ui.build(board.rows, board.cols, board.mines)
    ui.bind(game)

    # restore slot data if provided
    if slot_data is not None:
        ui.set_timer(slot_data.get("elapsed", 0))
        for r in range(board.rows):
            for c in range(board.cols):
                if board.revealed[r][c]:
                    ui.reveal_cell(r, c, board.grid[r][c])
        for (r, c) in sorted(board.flagged):
            ui.set_flag(r, c, True)

    # Protocol for window close: ask to save rather than directly closing unsaved
    def on_close():
        if game.game_over:
            try:
                ui.close()
            except Exception:
                pass
            try:
                game_root.destroy()
            except Exception:
                pass
            return

        ans = messagebox.askyesnocancel("Exit", "Save game before exiting?\nYes = Save & Exit\nNo = Exit without saving\nCancel = Return to game", parent=game_root)
        if ans is None:
            # Cancel => do nothing
            return
        if ans is True:
            # Save (synchronous prompt) then exit
            game.save_prompt()  # blocks until user closes save prompt (see game_logic.save_prompt implementation)
            try:
                ui.close()
            except Exception:
                pass
            try:
                game_root.destroy()
            except Exception:
                pass
            return
        else:
            # No -> exit without saving
            try:
                ui.close()
            except Exception:
                pass
            try:
                game_root.destroy()
            except Exception:
                pass
            return

    game_root.protocol("WM_DELETE_WINDOW", on_close)

    game.start(resume=(slot_data is not None), elapsed_before=(slot_data.get("elapsed", 0) if slot_data else 0))
    game_root.mainloop()


def main_menu(prefill_name=None):
    fm = FileManager()
    win = tk.Tk()
    win.title("Minesweeper - Menu")

    container = tk.Frame(win)
    container.pack()

    tk.Label(container, text="Minesweeper", font=("Arial", 18, "bold")).grid(row=0, column=0, pady=(12, 8))

    form = tk.Frame(container)
    form.grid(row=1, column=0, pady=(2, 8))

    tk.Label(form, text="Name:", width=8, anchor="e").grid(row=0, column=0, padx=6, pady=4)
    entry_name = tk.Entry(form, width=18)
    entry_name.grid(row=0, column=1, padx=6, pady=4)
    if prefill_name:
        entry_name.insert(0, prefill_name)
    else:
        entry_name.insert(0, "Player1")

    tk.Label(form, text="Rows:", width=8, anchor="e").grid(row=1, column=0, padx=6, pady=2)
    entry_rows = tk.Entry(form, width=6)
    entry_rows.grid(row=1, column=1, padx=6, pady=2)
    entry_rows.insert(0, str(DEFAULT_ROWS))

    tk.Label(form, text="Cols:", width=8, anchor="e").grid(row=2, column=0, padx=6, pady=2)
    entry_cols = tk.Entry(form, width=6)
    entry_cols.grid(row=2, column=1, padx=6, pady=2)
    entry_cols.insert(0, str(DEFAULT_COLS))

    tk.Label(form, text="Mines:", width=8, anchor="e").grid(row=3, column=0, padx=6, pady=2)
    entry_mines = tk.Entry(form, width=6)
    entry_mines.grid(row=3, column=1, padx=6, pady=2)
    entry_mines.insert(0, str(DEFAULT_MINES))

    def valid_name():
        n = entry_name.get().strip()
        if not n:
            messagebox.showerror("Missing name", "Please enter your name.")
            return None
        return n

    def start_custom():
        n = valid_name()
        if not n:
            return
        if not (entry_rows.get().isdigit() and entry_cols.get().isdigit() and entry_mines.get().isdigit()):
            messagebox.showerror("Error", "Row/Column/Mine values must be numeric.")
            return
        r = int(entry_rows.get()); c = int(entry_cols.get()); m = int(entry_mines.get())
        if m >= r * c:
            messagebox.showerror("Error", "Too many mines for this board.")
            return
        win.destroy()
        start_game(r, c, m, n, fm)

    def start_default():
        n = valid_name()
        if not n:
            return
        win.destroy()
        start_game(DEFAULT_ROWS, DEFAULT_COLS, DEFAULT_MINES, n, fm)

    btns = tk.Frame(container)
    btns.grid(row=2, column=0, pady=(4, 6))
    tk.Button(btns, text="Start (Custom)", width=16, command=start_custom).grid(row=0, column=0, padx=8)
    tk.Button(btns, text="Default (9×9, 15)", width=16, command=start_default).grid(row=0, column=1, padx=8)

    preset_label = tk.Label(container, text="Quick Presets:")
    preset_label.grid(row=3, column=0, pady=(6, 4))
    preset_frame = tk.Frame(container)
    preset_frame.grid(row=4, column=0)

    def start_preset(preset_tuple):
        n = valid_name()
        if not n:
            return
        r, c, m = preset_tuple
        win.destroy()
        start_game(r, c, m, n, fm)

    for i, (k, v) in enumerate(PRESETS.items()):
        tk.Button(preset_frame, text=k, width=10, command=(lambda p=v: start_preset(p))).grid(row=0, column=i, padx=6)

    lower = tk.Frame(container)
    lower.grid(row=5, column=0, pady=(6, 6))
    tk.Button(lower, text="Load Slot", width=12, command=lambda: load_slot_prompt(win, fm, entry_name)).grid(row=0, column=0, padx=6)
    tk.Button(lower, text="Leaderboard", width=12, command=lambda: fm.show_leaderboard(win)).grid(row=0, column=1, padx=6)
    tk.Button(lower, text="Clear Scores", width=12, command=fm.clear_scores).grid(row=0, column=2, padx=6)

    tk.Button(container, text="Exit", width=12, command=win.destroy).grid(row=6, column=0, pady=(6, 8))

    info = tk.Label(
        container,
        text="e3BV = Effective 3BV\nMinimum number of clicks required to solve the board\nafter your first move — without using flags.",
        font=("Arial", 9),
        fg="#555555",
        justify="center"
    )
    info.grid(row=7, column=0, pady=(4, 8))

    win.update_idletasks()
    w = win.winfo_reqwidth(); h = win.winfo_reqheight()
    win.geometry(f"{w+6}x{h+6}")
    win.resizable(False, False)

    win.mainloop()


def load_slot_prompt(win, fm, entry_widget):
    n = entry_widget.get().strip()
    if not n:
        messagebox.showerror("Missing name", "Enter your name")
        return
    dlg = tk.Toplevel(win)
    dlg.title("Load Slot")
    tk.Label(dlg, text="Choose slot to load:").grid(row=0, column=0, columnspan=3, pady=6)

    def do_load(slot):
        if not fm.slot_exists(slot):
            messagebox.showinfo("Load", f"Slot {slot} is empty.")
            return
        data = fm.read_slot(slot)
        if data is None:
            messagebox.showerror("Load", "Slot appears corrupted.")
            return
        dlg.destroy()
        win.destroy()
        # pass slot_index for automatic cleanup at game finish
        start_game(data["rows"], data["cols"], data["mines"], n, fm, slot_data=data, slot_index=slot)

    for i in range(1, 4):
        status = "Empty" if not fm.slot_exists(i) else "Occupied"
        tk.Button(dlg, text=f"Slot {i}\n({status})", width=12, command=lambda s=i: do_load(s)).grid(row=1, column=i - 1, padx=6, pady=6)


if __name__ == "__main__":
    main_menu()

