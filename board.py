# board.py
import random
from collections import deque

class Board:
    def __init__(self, rows, cols, mines, seed=None, grid=None, revealed=None, flagged=None):
        self.rows = rows
        self.cols = cols
        self.mines = mines
        self.seed = seed
        self.grid = grid
        self.revealed = revealed
        self.flagged = set(flagged) if flagged else set()
        self.mine_set = set()
        if self.grid is None or self.revealed is None:
            self._init_empty()
        self.placed = False

    def _init_empty(self):
        self.grid = [["0" for _ in range(self.cols)] for _ in range(self.rows)]
        self.revealed = [[False for _ in range(self.cols)] for _ in range(self.rows)]

    def place_mines(self, fixed_seed=None):
        if fixed_seed is not None:
            self.seed = int(fixed_seed)
            random.seed(self.seed)
        elif self.seed is not None:
            random.seed(int(self.seed))
        else:
            self.seed = random.randint(0, 10**9)
            random.seed(self.seed)

        self._init_empty()
        self.flagged = set()
        total = self.rows * self.cols
        positions = random.sample(range(total), self.mines)
        self.mine_set = set()
        for idx in positions:
            r, c = divmod(idx, self.cols)
            self.mine_set.add((r, c))
            self.grid[r][c] = "M"

        self._compute_numbers()
        if len(self.mine_set) != self.mines:
            remaining = [p for p in range(total) if (p // self.cols, p % self.cols) not in self.mine_set]
            while len(self.mine_set) < self.mines and remaining:
                p = random.choice(remaining)
                remaining.remove(p)
                rr, cc = divmod(p, self.cols)
                self.mine_set.add((rr, cc))
                self.grid[rr][cc] = "M"
            self._compute_numbers()
        return self.seed

    def place_mines_avoiding(self, avoid_cell):
        if self.seed is not None:
            random.seed(int(self.seed))
        else:
            self.seed = random.randint(0, 10**9)
            random.seed(self.seed)

        self._init_empty()
        self.flagged = set()

        ar, ac = avoid_cell
        banned = set()
        for i in range(-1, 2):
            for j in range(-1, 2):
                nr, nc = ar + i, ac + j
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    banned.add(nr * self.cols + nc)

        total = self.rows * self.cols
        allowed = [p for p in range(total) if p not in banned]

        if len(allowed) < self.mines:
            allowed = [p for p in range(total) if p != (ar * self.cols + ac)]

        positions = set()
        if len(allowed) >= self.mines:
            positions = set(random.sample(allowed, self.mines))
        else:
            candidates = [p for p in range(total) if p != (ar * self.cols + ac)]
            while len(positions) < self.mines and candidates:
                p = random.choice(candidates)
                candidates.remove(p)
                positions.add(p)

        self.mine_set = set()
        for idx in positions:
            r, c = divmod(idx, self.cols)
            self.mine_set.add((r, c))
            self.grid[r][c] = "M"

        if (ar, ac) in self.mine_set:
            self.mine_set.remove((ar, ac))
            self.grid[ar][ac] = "0"
            total_positions = set(range(self.rows * self.cols))
            remaining = list(total_positions - set(idx for idx in (p[0]*self.cols + p[1] for p in self.mine_set)) - {ar * self.cols + ac})
            if remaining:
                pick = random.choice(remaining)
                rr, cc = divmod(pick, self.cols)
                self.mine_set.add((rr, cc))
                self.grid[rr][cc] = "M"

        self._compute_numbers()
        if len(self.mine_set) != self.mines:
            total_positions = [(p // self.cols, p % self.cols) for p in range(self.rows * self.cols)]
            for (rr, cc) in total_positions:
                if len(self.mine_set) >= self.mines:
                    break
                if (rr, cc) not in self.mine_set and not (rr == ar and cc == ac):
                    self.mine_set.add((rr, cc))
                    self.grid[rr][cc] = "M"
            while len(self.mine_set) > self.mines:
                rem = next(iter(self.mine_set))
                if rem == (ar, ac):
                    break
                self.mine_set.remove(rem)
                self.grid[rem[0]][rem[1]] = "0"
            self._compute_numbers()

        return self.seed

    def _compute_numbers(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) in self.mine_set:
                    self.grid[r][c] = "M"
                    continue
                cnt = 0
                for i in range(-1, 2):
                    for j in range(-1, 2):
                        if i == 0 and j == 0:
                            continue
                        nr, nc = r + i, c + j
                        if 0 <= nr < self.rows and 0 <= nc < self.cols and (nr, nc) in self.mine_set:
                            cnt += 1
                self.grid[r][c] = str(cnt)

    def reveal(self, r, c):
        if self.revealed[r][c] or (r, c) in self.flagged:
            return []
        revealed_cells = []
        if self.grid[r][c] == "0":
            stack = [(r, c)]
            while stack:
                cr, cc = stack.pop()
                if self.revealed[cr][cc]:
                    continue
                self.revealed[cr][cc] = True
                revealed_cells.append((cr, cc, self.grid[cr][cc]))
                if self.grid[cr][cc] == "0":
                    for i in range(-1, 2):
                        for j in range(-1, 2):
                            nr, nc = cr + i, cc + j
                            if 0 <= nr < self.rows and 0 <= nc < self.cols and not self.revealed[nr][nc]:
                                stack.append((nr, nc))
        else:
            self.revealed[r][c] = True
            revealed_cells.append((r, c, self.grid[r][c]))
        return revealed_cells

    def toggle_flag(self, r, c):
        if self.revealed[r][c]:
            return None
        if (r, c) in self.flagged:
            self.flagged.remove((r, c))
            return False
        else:
            self.flagged.add((r, c))
            return True

    def check_win(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) not in self.mine_set and not self.revealed[r][c]:
                    return False
        return True

    def reveal_all_mines(self):
        return [(r, c, "M") for (r, c) in self.mine_set]

    def _reveal_simulation(self, start):
        sr, sc = start
        seen = set()
        if (sr, sc) in self.mine_set:
            return seen
        if self.grid[sr][sc] != "0":
            seen.add((sr, sc))
            return seen
        q = deque()
        q.append((sr, sc))
        seen.add((sr, sc))
        while q:
            r, c = q.popleft()
            if self.grid[r][c] == "0":
                for i in range(-1, 2):
                    for j in range(-1, 2):
                        nr, nc = r + i, c + j
                        if 0 <= nr < self.rows and 0 <= nc < self.cols and (nr, nc) not in seen:
                            seen.add((nr, nc))
                            if self.grid[nr][nc] == "0":
                                q.append((nr, nc))
        return seen

    def compute_e3bv(self, first_click=None):
        revealed_by_first = set()
        if first_click is not None:
            fr, fc = first_click
            if 0 <= fr < self.rows and 0 <= fc < self.cols:
                revealed_by_first = self._reveal_simulation(first_click)

        visited = set()
        zero_regions = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == "0" and (r, c) not in visited and (r, c) not in revealed_by_first:
                    zero_regions += 1
                    q = deque()
                    q.append((r, c)); visited.add((r, c))
                    while q:
                        cr, cc = q.popleft()
                        for i in range(-1, 2):
                            for j in range(-1, 2):
                                nr, nc = cr + i, cc + j
                                if 0 <= nr < self.rows and 0 <= nc < self.cols and (nr, nc) not in visited and (nr, nc) not in revealed_by_first:
                                    if self.grid[nr][nc] == "0":
                                        visited.add((nr, nc))
                                        q.append((nr, nc))

        zero_cells = set()
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == "0" and (r, c) not in revealed_by_first:
                    zero_cells.add((r, c))

        isolated_numbers = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) in self.mine_set:
                    continue
                if (r, c) in revealed_by_first:
                    continue
                if self.grid[r][c] == "0":
                    continue
                adj_to_zero = False
                for i in range(-1, 2):
                    for j in range(-1, 2):
                        nr, nc = r + i, c + j
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            if (nr, nc) in revealed_by_first or (nr, nc) in zero_cells:
                                adj_to_zero = True
                                break
                    if adj_to_zero:
                        break
                if not adj_to_zero:
                    isolated_numbers += 1

        e3bv = zero_regions + isolated_numbers
        return e3bv
