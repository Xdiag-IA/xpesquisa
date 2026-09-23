"""Inventário das distribuições instaladas; executar no ambiente do projeto."""
import importlib.metadata
import json
from pathlib import Path

items = []
for dist in importlib.metadata.distributions():
    meta = dist.metadata
    items.append({
        "name": meta["Name"], "version": dist.version,
        "license": meta.get("License-Expression") or meta.get("License"),
        "classifiers": [v for v in meta.get_all("Classifier", []) if v.startswith("License")],
        "license_files": [str(p) for p in (dist.files or []) if "license" in str(p).lower() or "notice" in str(p).lower()],
    })
Path("docs/dependency-licenses.json").write_text(
    json.dumps(sorted(items, key=lambda d: d["name"].lower()), indent=2, ensure_ascii=False), encoding="utf-8")
