# remember_problem_cell.py
from datetime import datetime


def remember_problem_cell(self, cell_path, color, guessed_label, distance, confidence):
    color_list = [int(c) for c in color]

    problem = {
        "cell": str(cell_path),
        "color": color_list,
        "guessed_label": str(guessed_label),
        "distance": float(distance),
        "confidence": float(confidence),
        "timestamp": datetime.now().isoformat(),
    }

    self.config_manager.problem_cells.append(problem)
    if len(self.config_manager.problem_cells) > 10:
        self.config_manager.problem_cells = self.config_manager.problem_cells[-50:]

    if len(self.config_manager.problem_cells) % 5 == 0:
        self.config_manager.save_problem_cells()
