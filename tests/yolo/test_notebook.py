"""Portable notebook syntax validation; does not pretend Colab was executed."""
import ast
import json
from pathlib import Path


def test_colab_notebook_cells_have_valid_python_and_no_fake_outputs():
    path=Path(__file__).resolve().parents[2]/"experiments/yolo/colab.ipynb"
    notebook=json.loads(path.read_text())
    assert notebook["nbformat"]==4
    for cell in notebook["cells"]:
        if cell["cell_type"]=="code":
            ast.parse("".join(cell["source"]))
            assert cell["execution_count"] is None and cell["outputs"]==[]
