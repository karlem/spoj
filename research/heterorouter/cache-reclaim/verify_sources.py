#!/usr/bin/env python3
"""Verify inspected source and installed skills against retained SHA256 manifests."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-root", type=Path, required=True)
    parser.add_argument("--kernel-root", type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    repo = here.parents[2]
    checked = []
    for filename, root, key in (("skills-install.json", repo, "installed_path"),
                                ("engine-sources.json", args.engine_root, "path"),
                                ("kernel-sources.json", args.kernel_root, "path")):
        manifest = json.loads((here / "evidence" / filename).read_text())
        for item in manifest["files"]:
            path = root / item[key]
            data = path.read_bytes()
            if len(data) != item["size"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise SystemExit("source mismatch: " + str(path))
            checked.append({"manifest": filename, "path": item[key]})
    print(json.dumps({"ok": True, "checked_files": len(checked),
                      "scope": "source identity only; no inference or physical comparison",
                      "checked": checked}, indent=2))


if __name__ == "__main__":
    main()
