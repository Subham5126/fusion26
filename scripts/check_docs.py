"""Verify local Markdown links; skip verbatim pack and archived originals."""
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = [p for p in ROOT.glob("*.md") if p.name != "CODEX_MASTER_PROMPT.md"]
    files += [p for folder in ("docs", "scripts", "tests", "data", "artifacts", "models")
              for p in (ROOT / folder).rglob("*.md") if "preparation" not in p.parts]
    errors = []
    count = 0
    for path in files:
        content = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            target = link.split("#", 1)[0]
            if not target or re.match(r"[a-z][a-z0-9+.-]*:", target, re.I):
                continue
            count += 1
            if not (path.parent / unquote(target)).exists():
                errors.append(f"{path.relative_to(ROOT)}: {link}")
    print(f"Checked {count} local links in {len(files)} Markdown files.")
    for error in errors:
        print(f"BROKEN: {error}")
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    main()
