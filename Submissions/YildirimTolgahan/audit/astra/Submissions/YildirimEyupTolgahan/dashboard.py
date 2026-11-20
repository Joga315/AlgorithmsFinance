"""Compile saved measurements into a portable, offline interactive report."""
import csv
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def read_csv(name):
    with (RESULTS / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def build():
    timings = read_csv("timings.csv")
    memory = read_csv("memory.csv")
    environment = json.loads((RESULTS / "environment.json").read_text(encoding="utf-8"))
    groups = {}
    for row in timings:
        key = tuple(row[k] for k in ("n", "q", "hits", "method", "version", "phase"))
        groups.setdefault(key, []).append(float(row["seconds"]))
    points = [dict(n=int(n), q=int(q), hits=int(h), method=m, version=v,
                   phase=p, us=median(values)*1e6)
              for (n, q, h, m, v, p), values in groups.items()]
    data = dict(points=points, memory=memory, environment=environment)
    template = (ROOT / "dashboard_template.html").read_text(encoding="utf-8")
    output = template.replace("__MEASUREMENTS__", json.dumps(data).replace("<", r"\u003c"))
    (ROOT / "dashboard.html").write_text(output, encoding="utf-8")


if __name__ == "__main__":
    build()
