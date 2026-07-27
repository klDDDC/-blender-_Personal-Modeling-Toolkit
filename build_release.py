"""Build a deterministic Blender add-on ZIP from the local source tree."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent
ADDON_DIR = ROOT / "uv_layer_manager_pro"


def read_addon_info():
    source = (ADDON_DIR / "__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(ADDON_DIR / "__init__.py"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "bl_info" for target in node.targets):
            continue
        info = ast.literal_eval(node.value)
        if not isinstance(info, dict) or "version" not in info:
            break
        return info
    raise ValueError("uv_layer_manager_pro/__init__.py does not define a literal bl_info version")


def version_text(info):
    version = tuple(info["version"])
    if len(version) != 3 or any(not isinstance(part, int) for part in version):
        raise ValueError(f"invalid add-on version: {version!r}")
    return ".".join(str(part) for part in version)


def source_files():
    if not ADDON_DIR.is_dir():
        raise FileNotFoundError(ADDON_DIR)
    files = []
    for path in ADDON_DIR.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        files.append(path)
    return sorted(files)


def archive_name(path):
    return "uv_layer_manager_pro/" + path.relative_to(ADDON_DIR).as_posix()


def build_archive(output):
    info = read_addon_info()
    version = version_text(info)
    files = source_files()
    if not files:
        raise ValueError("add-on source directory is empty")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            name = archive_name(path)
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, path.read_bytes())
    return info, version, files, output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="ZIP path or output directory (default: dist/)",
    )
    args = parser.parse_args()

    info = read_addon_info()
    version = version_text(info)
    output = args.output or (ROOT / "dist")
    if output.suffix.lower() != ".zip":
        output = output / f"UV_Layer_Manager_Pro-{version}.zip"

    info, version, files, output = build_archive(output)
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        invalid = [name for name in names if "__pycache__" in name or name.endswith((".pyc", ".pyo"))]
        if invalid or names != sorted(names):
            raise ValueError(f"invalid archive contents: {invalid!r}")

    print(json.dumps({
        "name": info.get("name", ""),
        "version": version,
        "file_count": len(files),
        "archive": str(output),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
