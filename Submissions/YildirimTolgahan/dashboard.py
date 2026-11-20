"""Build a deterministic offline dashboard from saved measurements."""
import argparse
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build(source, output):
    data = json.loads(source.read_text(encoding="utf-8"))
    if not data.get("rows"):
        raise ValueError("No saved measurements to display")
    reuse_path = source.parent / "reuse.json"
    if reuse_path.exists():
        data["reuse"] = json.loads(reuse_path.read_text(encoding="utf-8"))
    payload = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c")
    import os
    link = Path(os.path.relpath(source, output.parent)).as_posix()
    template = (HERE / "dashboard_template.html").read_text(encoding="utf-8")
    page = template.replace("__DATA__", payload).replace("__JSON_LINK__", html.escape(link, quote=True))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8", newline="\n")
    print(f"Dashboard: {output.resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=HERE / "results" / "measurements.json")
    parser.add_argument("--output", type=Path, default=HERE / "results" / "dashboard.html")
    args = parser.parse_args()
    build(args.results, args.output)


if __name__ == "__main__":
    main()
