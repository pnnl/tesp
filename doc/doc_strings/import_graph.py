"""Import Graph

Returns:
    _type_: _description_
"""
#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


TESPDIR = Path(r"C:\Users\kerb930\Documents\Transactive Energy\Community Engagement\doc_strings\tesp").resolve()


# Roots to scan
ROOTS = [
    TESPDIR / "src" / "tesp_support" / "tesp_support",
    TESPDIR / "examples" / "analysis" / "glm_dsot" / "code",
]

OUT_DIR = TESPDIR / "doc" / "doc_strings" / "import_graph_output"


@dataclass
class ModuleInfo:
    module: str
    file_path: Path
    root: Path


def to_module_name(root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]  # strip .py
    prefix = root.name  # tesp_support or code
    return ".".join([prefix] + parts)


def find_py_files(root: Path) -> List[Path]:
    return [p for p in root.rglob("*.py") if p.is_file()]


def resolve_relative_import(curr_mod: str, level: int, mod: Optional[str]) -> Optional[str]:
    # curr_mod is full module name, e.g. tesp_support.api.helpers
    parts = curr_mod.split(".")
    if not parts:
        return None
    # remove self module leaf (or keep package if __init__)
    base = parts[:-1]
    if level > len(base):
        return None
    anchor = base[: len(base) - level + 1] if level > 0 else base
    if mod:
        return ".".join(anchor + mod.split("."))
    return ".".join(anchor)


def parse_imports(file_path: Path, curr_module: str) -> List[Tuple[str, str, int]]:
    # returns list of (imported_module, import_type, line_no)
    imports = []
    try:
        src = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        src = file_path.read_text(encoding="latin-1")
    tree = ast.parse(src, filename=str(file_path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, "import", getattr(node, "lineno", -1)))
        elif isinstance(node, ast.ImportFrom):
            level = node.level or 0
            mod = node.module
            if level > 0:
                resolved = resolve_relative_import(curr_module, level, mod)
                if resolved:
                    imports.append((resolved, "from", getattr(node, "lineno", -1)))
            else:
                if mod:
                    imports.append((mod, "from", getattr(node, "lineno", -1)))
    return imports


def shorten(name: str) -> str:
    # cleaner labels in Mermaid
    return name.replace("tesp_support.", "ts.").replace("code.", "glm.")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build module index
    modules: Dict[str, ModuleInfo] = {}
    for root in ROOTS:
        if not root.exists():
            print(f"[WARN] Missing root: {root}")
            continue
        for py in find_py_files(root):
            mod = to_module_name(root, py)
            modules[mod] = ModuleInfo(mod, py, root)

    # Parse imports and classify
    internal_edges: List[Tuple[str, str, str, int]] = []
    external_edges: List[Tuple[str, str, str, int]] = []

    module_names = set(modules.keys())

    for mod, info in modules.items():
        imports = parse_imports(info.file_path, mod)
        for imp, imp_type, line_no in imports:
            # exact internal
            if imp in module_names:
                internal_edges.append((mod, imp, imp_type, line_no))
                continue

            # package-level internal match (e.g., "tesp_support.api")
            candidates = [m for m in module_names if m == imp or m.startswith(imp + ".")]
            if candidates:
                target = sorted(candidates, key=len)[0]
                internal_edges.append((mod, target, imp_type, line_no))
            else:
                external_edges.append((mod, imp, imp_type, line_no))

    # Write module index
    with (OUT_DIR / "module_index.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "file_path", "root"])
        for m in sorted(modules):
            mi = modules[m]
            w.writerow([mi.module, str(mi.file_path), str(mi.root)])

    # Write internal edges
    with (OUT_DIR / "import_edges.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["importer", "imported", "type", "line"])
        for row in sorted(set(internal_edges)):
            w.writerow(row)

    # Write external imports
    with (OUT_DIR / "external_imports.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["importer", "external_module", "type", "line"])
        for row in sorted(set(external_edges)):
            w.writerow(row)

    # Mermaid graph
    mermaid_lines = ["graph LR"]
    nodes: Set[str] = set()
    for a, b, _, _ in sorted(set(internal_edges)):
        na = shorten(a)
        nb = shorten(b)
        nodes.add(na)
        nodes.add(nb)
        mermaid_lines.append(f'  "{na}" --> "{nb}"')

    (OUT_DIR / "import_graph.mmd").write_text("\n".join(mermaid_lines), encoding="utf-8")

    # Graphviz DOT
    dot_lines = ["digraph imports {", "  rankdir=LR;"]
    for a, b, _, _ in sorted(set(internal_edges)):
        na = shorten(a).replace('"', '\\"')
        nb = shorten(b).replace('"', '\\"')
        dot_lines.append(f'  "{na}" -> "{nb}";')
    dot_lines.append("}")
    (OUT_DIR / "import_graph.dot").write_text("\n".join(dot_lines), encoding="utf-8")

    print(f"[OK] Wrote outputs to: {OUT_DIR}")
    print(f"     - module_index.csv")
    print(f"     - import_edges.csv")
    print(f"     - external_imports.csv")
    print(f"     - import_graph.mmd")
    print(f"     - import_graph.dot")


if __name__ == "__main__":
    main()