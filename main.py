# main.py — responsive, symmetric UI with polished visuals (canvas board)
import os
import tkinter as tk
from tkinter import messagebox, ttk
import sys
from board import Board
from game_logic import Game
from file_manager import FileManager

DEFAULT_ROWS, DEFAULT_COLS, DEFAULT_MINES = 9, 9, 15
PRESETS = {"Easy": (9, 9, 10), "Normal": (16, 16, 40), "Hard": (16, 30, 99)}

def center_window(win, width=None, height=None):
    win.update_idletasks()
    w = width or win.winfo_width()
    h = height or win.winfo_height()
    sw = win.winfo_screenwidth(); sh = win.winfo_screenheight()
    x = max(0, (sw // 2) - (w // 2))
    y = max(0, (sh // 2) - (h // 2))
    win.geometry(f"{w}x{h}+{x}+{y}")

class BoardUI:
    def __init__(self, root, player_name_cb):
        self.root = root
        self.player_name_cb = player_name_cb
        self._timer_job = None
        self._elapsed_fn = None
        self._cell_font_family = "Arial"
        self._items = {}
        self._best_cached = None
        self._hover_cell = None

    def build(self, rows, cols, mines):
        self.rows, self.cols, self.mines = rows, cols, mines
        for w in list(self.root.grid_slaves()): w.grid_forget()

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)

        header_frame = ttk.Frame(self.root, padding=(12,10))
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.columnconfigure(0, weight=1)

        chips = ttk.Frame(header_frame)
        chips.grid(row=0, column=0)
        chip_style = {"font":("Arial",11)}
        self.lbl_time = ttk.Label(chips, text="Time: 0s", **chip_style)
        self.lbl_time.pack(side="left", padx=(0,14))
        self.lbl_mines = ttk.Label(chips, text=f"Mines: {mines}", **chip_style)
        self.lbl_mines.pack(side="left", padx=(0,14))
        self.lbl_clicks = ttk.Label(chips, text="Clicks: 0", **chip_style)
        self.lbl_clicks.pack(side="left", padx=(0,14))

        middle = ttk.Frame(self.root, padding=12)
        middle.grid(row=1, column=0, sticky="nsew")
        middle.columnconfigure(0, weight=1); middle.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(middle, bg="#f7f7f8", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda e: self._redraw_debounced())
        self.root.bind("<Configure>", lambda e: self._redraw_debounced())

        self.canvas.bind("<Button-1>", lambda ev: self._on_canvas_click(ev, 1))
        self.canvas.bind("<Button-2>", lambda ev: self._on_canvas_click(ev, 2))
        self.canvas.bind("<Button-3>", lambda ev: self._on_canvas_click(ev, 3))
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)

        footer = ttk.Frame(self.root, padding=(10,12))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        actions = ttk.Frame(footer)
        actions.grid(row=0, column=0)
        ttk.Button(actions, text="Save", command=lambda: self._on_save(), width=14).pack(side="left", padx=8)
        ttk.Button(actions, text="Quit", command=self._on_quit, width=14).pack(side="left", padx=8)

        # internal drawing state
        self._cell_size = 28
        self._origin = (12,12)
        self._needs_full_redraw = True
        self._redraw_after_id = None
        self._redraw_board(force=True)

    def _on_canvas_click(self, ev, button):
        if not hasattr(self, "_game"): return
        r,c = self._coords_to_cell(ev.x, ev.y)
        if r is None: return
        if button == 1: self._game.on_left(r,c)
        elif button == 3: self._game.on_right(r,c)
        elif button == 2: self._game.on_middle(r,c)

    def _on_motion(self, ev):
        r,c = self._coords_to_cell(ev.x, ev.y)
        if (r,c) != self._hover_cell:
            if self._hover_cell is not None:
                self._set_cell_highlight(self._hover_cell[0], self._hover_cell[1], highlight=False)
            self._hover_cell = (r,c) if r is not None else None
            if self._hover_cell is not None:
                self._set_cell_highlight(r,c, highlight=True)

    def _on_leave(self, ev):
        if self._hover_cell is not None:
            self._set_cell_highlight(self._hover_cell[0], self._hover_cell[1], highlight=False)
            self._hover_cell = None

    def _coords_to_cell(self, x, y):
        ox, oy = self._origin
        cs = self._cell_size
        if x < ox or y < oy: return (None, None)
        c = int((x - ox) // cs)
        r = int((y - oy) // cs)
        if r < 0 or c < 0 or r >= self.rows or c >= self.cols: return (None, None)
        return r, c

    def _compute_layout(self, width=None, height=None):
        pad = 12
        w = width if width is not None else max(1, self.canvas.winfo_width())
        h = height if height is not None else max(1, self.canvas.winfo_height())
        if w <= 0 or h <= 0:
            return
        avail_w = max(1, w - 2*pad)
        avail_h = max(1, h - 2*pad)
        cs = min(avail_w // self.cols, avail_h // self.rows)
        cs = max(16, cs)
        total_w = cs * self.cols
        total_h = cs * self.rows
        ox = (w - total_w) // 2
        oy = (h - total_h) // 2
        self._cell_size = cs
        self._origin = (ox, oy)

    def _redraw_debounced(self, delay=40):
        if self._redraw_after_id:
            try: self.canvas.after_cancel(self._redraw_after_id)
            except Exception: pass
        self._redraw_after_id = self.canvas.after(delay, self._redraw_board)

    def _redraw_board(self, force=False):
        self._redraw_after_id = None
        self._compute_layout()
        ox, oy = self._origin; cs = self._cell_size
        if force or self._needs_full_redraw or not self._items:
            self.canvas.delete("all")
            self._items = {}
            bg_margin = int(cs * 0.08)
            total_w = cs * self.cols
            total_h = cs * self.rows
            self.canvas.create_rectangle(ox - bg_margin, oy - bg_margin,
                                         ox + total_w + bg_margin, oy + total_h + bg_margin,
                                         fill="#f3f4f6", outline="")
            for r in range(self.rows):
                for c in range(self.cols):
                    x1 = ox + c*cs; y1 = oy + r*cs
                    x2 = x1 + cs; y2 = y1 + cs
                    rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, fill="#f8f8f8", outline="#d0d0d5")
                    text_id = self.canvas.create_text(x1 + cs/2, y1 + cs/2, text="", font=(self._cell_font_family, max(9, int(cs*0.36)), "bold"))
                    self._items[(r,c)] = {"rect":rect_id, "text":text_id, "flag": None}
            self._needs_full_redraw = False
        else:
            for (r,c), ids in self._items.items():
                x1 = ox + c*cs; y1 = oy + r*cs
                x2 = x1 + cs; y2 = y1 + cs
                self.canvas.coords(ids["rect"], x1, y1, x2, y2)
                self.canvas.coords(ids["text"], x1 + cs/2, y1 + cs/2)
                if ids.get("flag"):
                    for fid in ids["flag"]:
                        self.canvas.coords(fid, x1 + cs*0.22, y1 + cs*0.2, x1 + cs*0.6, y1 + cs*0.33)

    def _set_cell_highlight(self, r, c, highlight=True):
        key = (r,c)
        item = self._items.get(key)
        if not item: return
        if highlight:
            self.canvas.itemconfigure(item["rect"], outline="#7077ff", width=2)
        else:
            self.canvas.itemconfigure(item["rect"], outline="#d0d0d5", width=1)

    def bind(self, game): self._game = game

    def reveal_cell(self, r, c, val):
        item = self._items.get((r,c))
        if not item:
            self._needs_full_redraw = True
            self._redraw_board(force=True)
            item = self._items.get((r,c))
            if not item: return
        rect = item["rect"]; txt = item["text"]
        if val == "M":
            self.canvas.itemconfigure(rect, fill="#ffd8d8", outline="#c94040")
            self.canvas.itemconfigure(txt, text="M", fill="#6b2b2b")
        elif val == "0":
            self.canvas.itemconfigure(rect, fill="#efefef", outline="#bfbfbf")
            self.canvas.itemconfigure(txt, text="")
        else:
            color = self._num_color(val)
            self.canvas.itemconfigure(rect, fill="#efefef", outline="#bfbfbf")
            self.canvas.itemconfigure(txt, text=str(val), fill=color)

    def reveal_mine(self, r, c):
        self.reveal_cell(r, c, "M")

    def set_flag(self, r, c, flagged):
        item = self._items.get((r,c))
        if not item:
            self._needs_full_redraw = True
            self._redraw_board(force=True)
            item = self._items.get((r,c))
            if not item: return
        rect_coords = self.canvas.coords(item["rect"])
        cs = self._cell_size
        if flagged:
            if not item.get("flag"):
                x1,y1,x2,y2 = rect_coords
                px = x1 + cs*0.22; py = y1 + cs*0.18
                tri = self.canvas.create_polygon(px, py+cs*0.14, px+cs*0.45, py+cs*0.28, px, py+cs*0.42, fill="#d23b3b", outline="")
                pole = self.canvas.create_line(px, py+cs*0.48, px, py+cs*0.06, fill="#5a3c2b", width=max(1,int(cs*0.06)))
                item["flag"] = (tri, pole)
                self.canvas.itemconfigure(item["rect"], fill="#fff6ea")
            else:
                for fid in item["flag"]:
                    self.canvas.itemconfigure(fid, state="normal")
        else:
            if item.get("flag"):
                for fid in item["flag"]:
                    try: self.canvas.delete(fid)
                    except: pass
                item["flag"] = None
            self.canvas.itemconfigure(item["rect"], fill="#f8f8f8")

    def update_counters(self, flagged_count, mines):
        remaining = max(0, mines - flagged_count)
        self.lbl_mines.config(text=f"Mines: {mines}  Remaining: {remaining}")

    def start_timer(self, elapsed_fn):
        self._elapsed_fn = elapsed_fn
        # ensure any previous job is cancelled
        try:
            if getattr(self, "_timer_job", None):
                self.root.after_cancel(self._timer_job)
        except Exception:
            pass
        self._tick()

    def _tick(self):
        # guard: do nothing if widget destroyed to avoid "invalid command name" errors
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return
        if not self._elapsed_fn:
            return
        try:
            self.lbl_time.config(text=f"Time: {self._elapsed_fn()}s")
            self._timer_job = self.root.after(1000, self._tick)
        except Exception:
            # if anything goes wrong (root destroyed etc.) stop scheduling
            try:
                if getattr(self, "_timer_job", None):
                    self.root.after_cancel(self._timer_job)
            except Exception:
                pass

    def set_timer(self, val): self.lbl_time.config(text=f"Time: {int(val)}s")
    def set_clicks(self, n): self.lbl_clicks.config(text=f"Clicks: {n}")
    def set_best(self, n): self._best_cached = n

    def _num_color(self, v):
        return {"1":"#2b5cff","2":"#0b8a3c","3":"#e13b3b","4":"#1a2f6b","5":"#7b2a2a","6":"#0b7b7b","7":"#000000","8":"#666666"}.get(str(v),"black")

    def close(self):
        try:
            if getattr(self, "_timer_job", None):
                self.root.after_cancel(self._timer_job)
            self.root.destroy()
        except Exception:
            pass

    def _on_save(self):
        if hasattr(self, "_game"): self._game.save_prompt()

    def _on_quit(self):
        if messagebox.askyesno("Quit", "Quit to desktop? Unsaved progress will be lost."):
            try: self.root.destroy()
            except: pass
            sys.exit(0)

# app flow
def start_game(rows, cols, mines, name, fm, slot=None):
    game_root = tk.Tk()
    game_root.title("Minesweeper")
    game_root.geometry("900x700")
    game_root.resizable(True, True)

    ui = BoardUI(game_root, lambda: name)
    if slot is None:
        board = Board(rows, cols, mines)
    else:
        board = Board(slot["rows"], slot["cols"], slot["mines"],
                    seed=slot.get("seed"), grid=slot.get("grid"),
                    revealed=slot.get("revealed"), flagged=slot.get("flagged"))

    def post_game(result, elapsed, clicks, best_possible):
        title = "Victory!" if result=="win" else "Game Over"
        best_txt = f"\nBest possible clicks: {best_possible}" if best_possible is not None else ""
        msg = f"{'You won!' if result=='win' else 'You lost!'}\nTime: {elapsed}s\nClicks: {clicks}{best_txt}\n\nPlay again? (Yes → Main Menu, No → Exit)"
        res = messagebox.askyesno(title, msg, parent=game_root)
        try: game_root.destroy()
        except: pass
        if res: main_menu(prefill_name=name)
        else: sys.exit(0)

    game = Game(board, fm, ui, post_game)
    if slot is not None:
        game.current_slot = slot.get("slot") if isinstance(slot, dict) else None

    ui.build(board.rows, board.cols, board.mines)
    ui.bind(game)

    if slot is not None:
        ui.set_timer(slot.get("elapsed",0))
        for r in range(board.rows):
            for c in range(board.cols):
                if board.revealed[r][c]:
                    ui.reveal_cell(r,c,board.grid[r][c])
        for (r,c) in sorted(board.flagged):
            ui.set_flag(r,c,True)

    game.start(resume=(slot is not None), elapsed_before=(slot.get("elapsed",0) if slot else 0))
    center_window(game_root, 900, 700)
    game_root.mainloop()

def main_menu(prefill_name=None):
    fm = FileManager()
    win = tk.Tk()
    win.title("Minesweeper - Menu")
    win.geometry("760x560")
    win.resizable(True, True)

    container = ttk.Frame(win, padding=18)
    container.pack(fill="both", expand=True)
    container.columnconfigure(0, weight=1)

    ttk.Label(container, text="Minesweeper", font=("Arial",24,"bold")).grid(row=0, column=0, pady=(0,14))

    form = ttk.Frame(container)
    form.grid(row=1, column=0, pady=(0,12), sticky="n")

    ttk.Label(form, text="Name:", width=10, anchor="e").grid(row=0, column=0, padx=6, pady=6)
    name_e = ttk.Entry(form, width=26); name_e.grid(row=0, column=1, padx=6, pady=6)
    if prefill_name: name_e.insert(0, prefill_name)
    else: name_e.insert(0, "Player1")

    # hide custom inline entries: will use dialog when Start (Custom) clicked
    def valid_name():
        n = name_e.get().strip()
        if not n:
            messagebox.showerror("Missing name","Please enter name"); return None
        return n

    def start_custom_dialog():
        n = valid_name()
        if not n: return
        dlg = tk.Toplevel(win)
        dlg.title("Custom Game")
        dlg.transient(win)
        dlg.grab_set()
        ttk.Label(dlg, text="Rows:").grid(row=0, column=0, padx=6, pady=6)
        r_e = ttk.Entry(dlg, width=8); r_e.grid(row=0, column=1, padx=6, pady=6); r_e.insert(0,str(DEFAULT_ROWS))
        ttk.Label(dlg, text="Cols:").grid(row=1, column=0, padx=6, pady=6)
        c_e = ttk.Entry(dlg, width=8); c_e.grid(row=1, column=1, padx=6, pady=6); c_e.insert(0,str(DEFAULT_COLS))
        ttk.Label(dlg, text="Mines:").grid(row=2, column=0, padx=6, pady=6)
        m_e = ttk.Entry(dlg, width=8); m_e.grid(row=2, column=1, padx=6, pady=6); m_e.insert(0,str(DEFAULT_MINES))

        def do_start():
            if not (r_e.get().isdigit() and c_e.get().isdigit() and m_e.get().isdigit()):
                messagebox.showerror("Error","Numeric values required"); return
            r,c,m = int(r_e.get()), int(c_e.get()), int(m_e.get())
            if m >= r*c:
                messagebox.showerror("Error","Too many mines"); return
            dlg.destroy(); win.destroy(); start_game(r,c,m,n,fm)

        ttk.Button(dlg, text="Start", command=do_start).grid(row=3, column=0, columnspan=2, pady=8)

    def start_default():
        n = valid_name(); 
        if not n: return
        win.destroy(); start_game(DEFAULT_ROWS, DEFAULT_COLS, DEFAULT_MINES, n, fm)

    btns = ttk.Frame(container)
    btns.grid(row=2, column=0, pady=(0,8))
    ttk.Button(btns, text="Start (Custom)", width=18, command=start_custom_dialog).grid(row=0, column=0, padx=10)
    ttk.Button(btns, text=f"Default ({DEFAULT_ROWS}×{DEFAULT_COLS},{DEFAULT_MINES})", width=26, command=start_default).grid(row=0, column=1, padx=10)

    # presets
    preset_lbl = ttk.Label(container, text="Quick Presets", font=("Arial",12,"bold"))
    preset_lbl.grid(row=3, column=0, pady=(14,8))
    preset_frame = ttk.Frame(container)
    preset_frame.grid(row=4, column=0, pady=(0,12), sticky="ew")
    for i in range(len(PRESETS)):
        preset_frame.columnconfigure(i, weight=1)

    preset_list = list(PRESETS.items())
    for i, (preset_name, vals) in enumerate(preset_list):
        rows_p, cols_p, mines_p = vals
        def make_cmd(r=rows_p, c=cols_p, m=mines_p):
            def cmd():
                n = name_e.get().strip()
                if not n:
                    messagebox.showerror("Missing name", "Please enter name")
                    return
                win.destroy()
                start_game(r, c, m, n, fm)
            return cmd
        # very small block padding and practically no gap
        block = ttk.Frame(preset_frame, padding=2, relief="flat")
        block.grid(row=0, column=i, padx=2, pady=2)
        ttk.Button(block, text=preset_name, width=12, command=make_cmd()).pack(ipadx=2, ipady=2)
        ttk.Label(block, text=f"{rows_p}×{cols_p}  Mines:{mines_p}", justify="center", font=("Arial",9)).pack(pady=(2,0))



    lower = ttk.Frame(container)
    lower.grid(row=5, column=0, pady=(6,10))

    def clear_scores_action():
        if os.path.exists(fm.score_file):
            if messagebox.askyesno("Confirm", "Clear leaderboard?"):
                try:
                    os.remove(fm.score_file)
                    messagebox.showinfo("Done", "Leaderboard cleared.")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not clear scores: {e}")
        else:
            messagebox.showinfo("Info", "Leaderboard already empty.")

    ttk.Button(lower, text="Load Slot", width=16, command=lambda: load_slot_prompt(win,fm,name_e)).grid(row=0,column=0, padx=8)
    ttk.Button(lower, text="Leaderboard", width=16, command=lambda: fm.show_personal_leaderboard(win, name_e.get().strip())).grid(row=0,column=1, padx=8)
    ttk.Button(lower, text="Clear Scores", width=16, command=clear_scores_action).grid(row=0,column=2, padx=8)

    ttk.Button(container, text="Exit", width=16, command=win.destroy).grid(row=6, column=0, pady=(8,0))
    center_window(win, 760, 560)
    win.mainloop()

def load_slot_prompt(win,fm,entry_widget):
    n = entry_widget.get().strip()
    if not n:
        messagebox.showerror("Missing name","Enter your name"); return
    dlg = tk.Toplevel(win); dlg.title("Load Slot")
    dlg.transient(win); dlg.resizable(False, False)
    ttk.Label(dlg, text="Choose slot to load:").grid(row=0, column=0, columnspan=3, pady=10, padx=12)
    def do_load(s):
        if not fm.slot_exists(s): messagebox.showinfo("Load",f"Slot {s} empty"); return
        data = fm.read_slot(s)
        if data is None: messagebox.showerror("Load","Slot corrupted"); return
        data["slot"] = s
        dlg.destroy(); win.destroy(); start_game(data["rows"],data["cols"],data["mines"], n, fm, slot=data)
    for i in range(1,4):
        status = "Empty" if not fm.slot_exists(i) else "Occupied"
        ttk.Button(dlg, text=f"Slot {i}\n({status})", width=16, command=lambda s=i: do_load(s)).grid(row=1,column=i-1,padx=8,pady=8)

if __name__ == "__main__":
    main_menu()
