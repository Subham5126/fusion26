"""Compile and import every bootstrap package plus the declared CPU libraries."""
import compileall
import importlib
from pathlib import Path
import pkgutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    for folder in ("backend", "scripts", "tests"):
        if not compileall.compile_dir(ROOT / folder, quiet=1):
            raise SystemExit(1)
    count = 0
    for name in ("app", "orbittrace"):
        package = importlib.import_module(name)
        for info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            importlib.import_module(info.name)
            count += 1
    for name in ("numpy", "cv2", "scipy", "PIL", "pydantic", "fastapi", "uvicorn", "yaml", "python_multipart"):
        importlib.import_module(name)
    print(f"Python {sys.version.split()[0]}: {count} package modules and all CPU dependencies import successfully.")


if __name__ == "__main__":
    main()
