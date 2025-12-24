# find_all_chains.py
import constants as const


def find_all_chains(self):
    directions = [
        (0, 1),
        (1, 0),
        (0, -1),
        (-1, 0),
        (1, 1),
        (1, -1),
        (-1, 1),
        (-1, -1),
    ]

    all_chains = []

    for r in range(const.ROWS):
        for c in range(const.COLS):
            start_val = self.board[r][c]
            if start_val <= 0:
                continue

            stack = [([(r, c)], start_val, {(r, c)})]

            while stack:
                current_path, current_val, visited = stack.pop()

                if len(current_path) >= 2:
                    if self.is_valid_chain(current_path):
                        all_chains.append(current_path.copy())

                last_r, last_c = current_path[-1]

                for dr, dc in directions:
                    nr, nc = last_r + dr, last_c + dc

                    if not (0 <= nr < const.ROWS and 0 <= nc < const.COLS):
                        continue
                    if (nr, nc) in visited:
                        continue

                    next_val = self.board[nr][nc]
                    if next_val <= 0:
                        continue

                    if next_val == current_val or next_val == current_val * 2:
                        new_path = current_path + [(nr, nc)]
                        new_visited = visited.copy()
                        new_visited.add((nr, nc))
                        stack.append((new_path, next_val, new_visited))
    print("ALL CHIANS")
    return self._filter_chains(all_chains)
