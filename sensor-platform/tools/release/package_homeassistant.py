from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Package Home Assistant/HACS artifacts.")
    parser.add_argument("--version", required=True, help="Package version string.")
    parser.add_argument("--output", required=True, help="Output directory.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    output_dir = Path(args.output).resolve()
    staging_dir = output_dir / f"nowacontrol_hydraulic_sensor-{args.version}"
    zip_base = output_dir / f"nowacontrol_hydraulic_sensor-ha-{args.version}"

    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    component_source = repo_root / "custom_components" / "nowacontrol_hydraulic_sensor"
    component_target = staging_dir / "custom_components" / "nowacontrol_hydraulic_sensor"
    component_target.parent.mkdir(parents=True, exist_ok=True)
    (staging_dir / "zha_quirks").mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        component_source,
        component_target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )

    shutil.copy2(repo_root / "hacs.json", staging_dir / "hacs.json")
    shutil.copy2(
        component_source / "quirks" / "nowacontrol_hydraulic_sensor_v1.py",
        staging_dir / "zha_quirks" / "nowacontrol_hydraulic_sensor_v1.py",
    )
    shutil.copy2(
        component_source / "quirks" / "README.md",
        staging_dir / "zha_quirks" / "README.md",
    )

    metadata = {
        "version": args.version,
        "package": "nowacontrol_hydraulic_sensor",
        "hacs_repository_root": False,
    }
    (staging_dir / "package.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    shutil.make_archive(str(zip_base), "zip", staging_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
