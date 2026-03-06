#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Finding:
    file: str
    symbol_type: str
    symbol_name: str
    line: int
    status: str  # missing | present_short | present_ok
    length: int


def get_tespdir() -> Path:
    # raw = os.environ.get("TESPDIR")
    # if not raw:
    #     raise EnvironmentError("TESPDIR is not set.")
    # return Path(raw.strip().strip('"').strip("'")).resolve()
    TESPDIR = Path(r"C:\Users\kerb930\Documents\Transactive Energy\Community Engagement\doc_strings\tesp").resolve()
    return TESPDIR

def check_docstring(node: ast.AST) -> tuple[str, int]:
    ds = ast.get_docstring(node, clean=False)
    if ds is None:
        return "missing", 0
    n = len(ds.strip())
    if n < 30:
        return "present_short", n
    return "present_ok", n


def analyze_file(py_file: Path) -> List[Finding]:
    findings: List[Finding] = []
    src = py_file.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src, filename=str(py_file))

    # module docstring
    status, n = check_docstring(tree)
    findings.append(Finding(str(py_file), "module", py_file.stem, 1, status, n))

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            status, n = check_docstring(node)
            findings.append(
                Finding(str(py_file), "class", node.name, node.lineno, status, n)
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            status, n = check_docstring(node)
            findings.append(
                Finding(str(py_file), "function", node.name, node.lineno, status, n)
            )
    return findings


def main() -> None:
    tespdir = get_tespdir()
    roots = [
        tespdir / "src" / "tesp_support" / "tesp_support" / "api",
        tespdir / "src" / "tesp_support" / "tesp_support" / "dsot",
    ]
    out_dir = tespdir / "doc" / "doc_strings" / "audit_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    py_files: List[Path] = []
    for root in roots:
        if root.exists():
            py_files.extend(root.rglob("*.py"))

    all_findings: List[Finding] = []
    for f in sorted(py_files):
        all_findings.extend(analyze_file(f))

    out_csv = out_dir / "docstring_audit.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "symbol_type", "symbol_name", "line", "status", "length"])
        for x in all_findings:
            w.writerow([x.file, x.symbol_type, x.symbol_name, x.line, x.status, x.length])

    # summary
    counts = {"missing": 0, "present_short": 0, "present_ok": 0}
    for x in all_findings:
        counts[x.status] += 1

    print(f"[OK] Wrote: {out_csv}")
    print(f"[SUMMARY] missing={counts['missing']}, short={counts['present_short']}, ok={counts['present_ok']}")


if __name__ == "__main__":
    main()