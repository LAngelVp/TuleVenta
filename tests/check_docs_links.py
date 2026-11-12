import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


def headings(path):
    anchors = set()
    counts = {}
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    for title in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", text, re.M):
        title = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", title).lower()
        anchor = "".join(character for character in title
                         if character in "_- " or unicodedata.category(character)[0] in "LNM")
        anchor = anchor.replace(" ", "-")
        count = counts.get(anchor, 0)
        counts[anchor] = count + 1
        anchors.add(f"{anchor}-{count}" if count else anchor)
    return anchors


def main():
    checked = 0
    broken = []
    for document in sorted((ROOT / "docs").rglob("*.md")):
        text = re.sub(r"```.*?```", "", document.read_text(encoding="utf-8"), flags=re.S)
        for target in re.findall(r"(?<!!)\[[^]\n]+\]\(([^)\n]+)\)", text):
            parts = urlsplit(target.strip())
            if parts.scheme or parts.netloc:
                continue
            path = (document.parent / unquote(parts.path)).resolve() if parts.path else document
            checked += 1
            error = None
            if not path.exists():
                error = "destino inexistente"
            elif parts.fragment and path.suffix == ".md" and unquote(parts.fragment) not in headings(path):
                error = "ancla inexistente"
            elif parts.fragment and path.suffix != ".md":
                match = re.fullmatch(r"L(\d+)(?:-L(\d+))?", parts.fragment)
                if match and int(match.group(2) or match.group(1)) > len(path.read_text(encoding="utf-8").splitlines()):
                    error = "linea inexistente"
            if error:
                broken.append(f"{document.relative_to(ROOT)}: {target}: {error}")
    print(f"Enlaces locales comprobados: {checked}; errores: {len(broken)}")
    for error in broken:
        print(error)
    return bool(broken)


if __name__ == "__main__":
    sys.exit(main())