"""Recheck the preserved Astra archive, results, export and bundled history."""
import csv
from collections import defaultdict
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SUBMISSION = HERE.parent
SOURCE = HERE / "astra" / "Submissions" / "YildirimEyupTolgahan"
WORK = HERE / ".work"

if not __debug__:
    raise SystemExit("Verification requires assertions. Run Python without -O or -OO.")


def command(args, cwd=None):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def write_log(path, text):
    path.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n",
                    encoding="utf-8", newline="\n")


def verify():
    WORK.mkdir(exist_ok=True)
    environment = json.loads((SOURCE / "results/environment.json").read_text())
    for name, digest in environment["source_sha256"].items():
        assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == digest, name
    times = list(csv.DictReader(io.StringIO((SOURCE / "results/timings.csv").read_text())))
    memory = list(csv.DictReader(io.StringIO((SOURCE / "results/memory.csv").read_text())))
    groups = defaultdict(list)
    for row in times:
        assert math.isfinite(float(row["seconds"])) and float(row["seconds"]) > 0
        assert 1 <= int(row["calls"]) <= 20000
        assert float(row["hit_rate"]) == int(row["hits"]) / int(row["q"])
        key = tuple(row[k] for k in ("n", "q", "hits", "method", "version", "phase"))
        groups[key].append(row)
    assert len(times) == 1350 and len(groups) == 270
    for group in groups.values():
        assert sorted(int(row["repeat"]) for row in group) == [1, 2, 3, 4, 5]
    memory_keys = set()
    for row in memory:
        assert int(row["peak_bytes"]) >= int(row["current_bytes"]) >= 0
        memory_keys.add(tuple(row[k] for k in ("n", "q", "hits", "method", "version")))
    assert len(memory_keys) == len(memory) == 90
    assert {key[:-1] for key in groups} == memory_keys
    claim = {}
    for method in ("linear", "binary", "hash"):
        for version in ("original", "revised"):
            claim[method + "/" + version] = {
                phase + "_us": statistics.median(float(r["seconds"]) for r in groups["100000", "100", "50", method, version, phase]) * 1e6
                for phase in ("prepare", "batch", "total")}
    assert round(claim["binary/original"]["batch_us"]) == 117
    assert round(claim["binary/revised"]["batch_us"]) == 99
    assert round(claim["hash/revised"]["total_us"] / 1000, 2) == 2.09

    rebuild = WORK / "rebuild"
    shutil.copytree(SOURCE, rebuild, dirs_exist_ok=True)
    command([sys.executable, "-B", "dashboard.py"], cwd=rebuild)
    rebuilt_html = (rebuild / "dashboard.html").read_bytes()
    supplied_html = (SOURCE / "dashboard.html").read_bytes()
    byte_identical = rebuilt_html == supplied_html
    assert rebuilt_html.replace(b"\r\n", b"\n") == supplied_html.replace(b"\r\n", b"\n")
    latest_test = subprocess.run([sys.executable, "-B", "-m", "unittest", "-v"], cwd=rebuild, text=True, capture_output=True)
    write_log(HERE / "astra_tests.txt", latest_test.stdout + latest_test.stderr)
    assert latest_test.returncode == 0

    history = WORK / "history.git"
    if not history.exists():
        command(["git", "clone", "--bare", "--shared", str(SUBMISSION.parents[1]), str(history)])
    git = ["git", "--git-dir=" + str(history)]
    command(git + ["fetch", str(HERE / "astra/Phase1.bundle"), "refs/heads/submission/yildirim-eyup-tolgahan:refs/heads/astra"])
    log = command(git + ["log", "--oneline", "d96deb0..astra"])
    history_results = {}
    for commit in ("244c6f0", "c1d45f3", "a82224a"):
        checkout = WORK / commit
        checkout.mkdir(exist_ok=True)
        for name in ("searches.py", "synthetic_data.py", "test_search.py"):
            content = command(git + ["show", commit + ":Submissions/YildirimEyupTolgahan/" + name])
            (checkout / name).write_text(content, encoding="utf-8")
        selection = ["test_search.MembershipTests.test_slide_example"] if commit == "244c6f0" else []
        run = subprocess.run([sys.executable, "-B", "-m", "unittest", *selection, "-v"], cwd=checkout, text=True, capture_output=True)
        text = run.stdout + run.stderr
        write_log(HERE / ("history_" + commit + ".txt"), text)
        if commit == "244c6f0":
            assert run.returncode != 0 and "FAILED (failures=3)" in text
        else:
            assert run.returncode == 0
        history_results[commit] = {"exit_code": run.returncode, "expected_outcome_confirmed": True}
    report = {
        "audit_python": sys.version,
        "source_hashes_match": True, "timing_records": len(times), "allocation_records": len(memory),
        "dashboard_rebuild_byte_identical": byte_identical,
        "dashboard_rebuild_identical_after_newline_normalization": True,
        "provided_tests_pass": True,
        "history_results": history_results, "bundle_commits": log.splitlines(),
        "claimed_workload_medians": claim,
        "limits": "Saved Astra timings are arithmetically verified, not rerun on its Linux host. No universal or statistically established speedup is inferred from five repeats.",
    }
    (HERE / "astra_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    verify()
