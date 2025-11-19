import random
from collections import deque

def neighbors(r,c,rows,cols):
    for dr in (-1,0,1):
        for dc in (-1,0,1):
            if dr==0 and dc==0: continue
            nr, nc = r+dr, c+dc
            if 0 <= nr < rows and 0 <= nc < cols:
                yield nr, nc

class Board:
    def __init__(self, rows, cols, mines, seed=None, grid=None, revealed=None, flagged=None):
        self.rows = int(rows); self.cols = int(cols); self.mines = int(mines)
        self.seed = None if seed in (None, '?') else int(seed) if seed is not None else None
        self._rand = None
        self.grid = grid
        self.revealed = revealed
        self.flagged = set(flagged) if flagged else set()
        self.mine_set = set()
        self.placed = False
        if self.grid is not None and self.revealed is not None:
            self.mine_set = set((r,c) for r in range(self.rows) for c in range(self.cols) if self.grid[r][c]=="M")
            self.placed = True
        else:
            self._init_empty()

    def _init_empty(self):
        self.grid = [["0"]*self.cols for _ in range(self.rows)]
        self.revealed = [[False]*self.cols for _ in range(self.rows)]
        self.flagged = set(); self.mine_set = set(); self.placed=False

    def _ensure_rng(self):
        if self._rand is not None: return
        if self.seed is None: self.seed = random.randint(0,10**9)
        self._rand = random.Random(int(self.seed))

    def place_mines(self, fixed_seed=None):
        if fixed_seed is not None:
            self.seed = int(fixed_seed); self._rand = random.Random(self.seed)
        else:
            self._ensure_rng()
        self.grid = [["0"]*self.cols for _ in range(self.rows)]
        self.revealed = [[False]*self.cols for _ in range(self.rows)]
        self.flagged = set()
        total = self.rows*self.cols
        pos = self._rand.sample(range(total), self.mines)
        self.mine_set = set()
        for idx in pos:
            r,c = divmod(idx, self.cols)
            self.grid[r][c] = "M"; self.mine_set.add((r,c))
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c]=="M": continue
                cnt=0
                for nr,nc in neighbors(r,c,self.rows,self.cols):
                    if self.grid[nr][nc]=="M": cnt+=1
                self.grid[r][c]=str(cnt)
        self.placed=True
        return self.seed

    def place_mines_avoiding(self, avoid_pos, fixed_seed=None):
        if fixed_seed is not None:
            self.seed = int(fixed_seed); self._rand = random.Random(self.seed)
        else:
            self._ensure_rng()
        ar,ac = avoid_pos
        banned = set([avoid_pos]) | set(neighbors(ar,ac,self.rows,self.cols))
        choices = [(r,c) for r in range(self.rows) for c in range(self.cols) if (r,c) not in banned]
        if len(choices) < self.mines:
            choices = [(r,c) for r in range(self.rows) for c in range(self.cols)]
        picked = self._rand.sample(choices, self.mines)
        self.mine_set = set(picked)
        self.grid = [["0"]*self.cols for _ in range(self.rows)]
        for r,c in self.mine_set: self.grid[r][c]="M"
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c]=="M": continue
                cnt=0
                for nr,nc in neighbors(r,c,self.rows,self.cols):
                    if self.grid[nr][nc]=="M": cnt+=1
                self.grid[r][c]=str(cnt)
        self.revealed = [[False]*self.cols for _ in range(self.rows)]
        self.flagged = set()
        self.placed = True
        return self.seed

    def reveal(self, r, c):
        if self.revealed[r][c] or (r,c) in self.flagged: return []
        out=[]
        if self.grid[r][c]=="0":
            dq=deque([(r,c)])
            while dq:
                cr,cc = dq.popleft()
                if self.revealed[cr][cc]: continue
                self.revealed[cr][cc]=True
                out.append((cr,cc,self.grid[cr][cc]))
                if self.grid[cr][cc]=="0":
                    for nr,nc in neighbors(cr,cc,self.rows,self.cols):
                        if not self.revealed[nr][nc] and (nr,nc) not in self.flagged: dq.append((nr,nc))
        else:
            self.revealed[r][c]=True
            out.append((r,c,self.grid[r][c]))
        return out

    def chord(self, r, c):
        if not self.revealed[r][c]: return []
        val = self.grid[r][c]
        if val in ("0","M"): return []
        need = int(val)
        neigh = list(neighbors(r,c,self.rows,self.cols))
        flagged = sum(1 for p in neigh if p in self.flagged)
        if flagged != need: return []
        res=[]
        for nx,ny in neigh:
            if (nx,ny) not in self.flagged and not self.revealed[nx][ny]:
                res += self.reveal(nx,ny)
        return res

    def toggle_flag(self, r, c):
        if self.revealed[r][c]: return None
        if (r,c) in self.flagged:
            self.flagged.remove((r,c)); return False
        else:
            self.flagged.add((r,c)); return True

    def check_win(self):
        safe = self.rows*self.cols - self.mines
        revealed_safe = sum(1 for r in range(self.rows) for c in range(self.cols) if self.revealed[r][c] and self.grid[r][c]!="M")
        return revealed_safe == safe

    def reveal_all_mines(self):
        return [(r,c,"M") for (r,c) in sorted(self.mine_set)]

    def compute_min_clicks(self):
        rows,cols = self.rows, self.cols
        visited_zero = [[False]*cols for _ in range(rows)]
        zeros_comp = 0
        from collections import deque
        for r in range(rows):
            for c in range(cols):
                if self.grid[r][c]=="0" and not visited_zero[r][c]:
                    zeros_comp += 1
                    dq = deque([(r,c)]); visited_zero[r][c]=True
                    while dq:
                        cr,cc = dq.popleft()
                        for nr,nc in neighbors(cr,cc,rows,cols):
                            if self.grid[nr][nc]=="0" and not visited_zero[nr][nc]:
                                visited_zero[nr][nc]=True; dq.append((nr,nc))
        revealed_by_zero = set()
        for r in range(rows):
            for c in range(cols):
                if self.grid[r][c]=="0" and visited_zero[r][c]:
                    revealed_by_zero.add((r,c))
                    for nr,nc in neighbors(r,c,rows,cols): revealed_by_zero.add((nr,nc))
        remaining_safe = sum(1 for r in range(rows) for c in range(cols) if self.grid[r][c]!="M" and (r,c) not in revealed_by_zero)
        return zeros_comp + remaining_safe
