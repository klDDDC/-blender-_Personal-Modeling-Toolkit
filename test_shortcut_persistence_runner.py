"""Run shortcut persistence checks in two isolated Blender processes."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent
ADDON_SOURCE = ROOT / "uv_layer_manager_pro"
BLENDER_TEST = ROOT / "test_shortcut_persistence_blender.py"


def run_stage(blender, scripts_root, config_root, stage):
    env = os.environ.copy()
    env["BLENDER_USER_SCRIPTS"] = str(scripts_root)
    env["BLENDER_USER_CONFIG"] = str(config_root)
    env["UVLM_SHORTCUT_STAGE"] = stage
    result = subprocess.run(
        [str(blender), "--background", "--python", str(BLENDER_TEST)],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    if result.returncode:
        raise SystemExit(f"shortcut persistence {stage} stage failed with exit code {result.returncode}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", type=Path, required=True)
    args = parser.parse_args()
    blender = args.blender.resolve()
    if not blender.is_file():
        raise FileNotFoundError(blender)

    with tempfile.TemporaryDirectory(prefix="uvlm-shortcut-test-") as temp_dir:
        temp_root = Path(temp_dir)
        scripts_root = temp_root / "scripts"
        config_root = temp_root / "config"
        addon_target = scripts_root / "addons" / ADDON_SOURCE.name
        addon_target.parent.mkdir(parents=True)
        config_root.mkdir()
        shutil.copytree(ADDON_SOURCE, addon_target)
        run_stage(blender, scripts_root, config_root, "write")
        run_stage(blender, scripts_root, config_root, "read")
    print("UVLM_SHORTCUT_TEST_SUMMARY 2/2 PASS")


if __name__ == "__main__":
    main()
