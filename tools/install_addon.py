"""Build and atomically install the add-on into a Blender user directory."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

from build_release import ROOT, build_archive, read_addon_info, version_text


ADDON_NAME = "uv_layer_manager_pro"


def default_addon_root(blender_version):
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise EnvironmentError("APPDATA is not defined; pass --addon-root explicitly")
    return Path(appdata) / "Blender Foundation" / "Blender" / blender_version / "scripts" / "addons"


def install(blender_version, addon_root=None):
    info = read_addon_info()
    version = version_text(info)
    archive = ROOT / "dist" / f"UV_Layer_Manager_Pro-{version}.zip"
    build_archive(archive)

    addon_root = Path(addon_root) if addon_root else default_addon_root(blender_version)
    addon_root = addon_root.expanduser().resolve()
    target = (addon_root / ADDON_NAME).resolve()
    if target.parent != addon_root:
        raise ValueError("refusing to install outside the selected Blender add-on directory")

    addon_root.mkdir(parents=True, exist_ok=True)
    backup = addon_root / f".{ADDON_NAME}.backup"
    if backup.exists():
        shutil.rmtree(backup)

    with tempfile.TemporaryDirectory(prefix=".uvlm-install-", dir=addon_root) as staging_dir:
        staging_root = Path(staging_dir)
        with zipfile.ZipFile(archive) as package:
            package.extractall(staging_root)
        staged_addon = staging_root / ADDON_NAME
        if not (staged_addon / "__init__.py").is_file():
            raise ValueError("release archive does not contain a valid add-on root")

        replaced = target.exists()
        if replaced:
            target.rename(backup)
        try:
            # Create the final directory in-place so Windows inherits the
            # Blender add-on root ACL. Moving a privileged temp directory can
            # otherwise leave normal Blender processes unable to read it.
            target.mkdir()
            shutil.copytree(staged_addon, target, dirs_exist_ok=True)
        except Exception:
            if target.exists():
                shutil.rmtree(target)
            if backup.exists():
                backup.rename(target)
            raise
        if backup.exists():
            shutil.rmtree(backup)

    return {
        "name": info.get("name", ""),
        "version": version,
        "archive": str(archive),
        "target": str(target),
        "replaced_existing": replaced,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender-version", default="4.1")
    parser.add_argument("--addon-root", type=Path)
    args = parser.parse_args()
    print(json.dumps(install(args.blender_version, args.addon_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
