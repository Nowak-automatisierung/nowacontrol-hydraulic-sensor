from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_info(path: Path) -> dict[str, object]:
    return {
        "filename": path.name,
        "size": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OTA release manifest.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--app-hex", required=True)
    parser.add_argument("--app-bin", required=True)
    parser.add_argument("--bootloader", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    app_hex = Path(args.app_hex).resolve()
    app_bin = Path(args.app_bin).resolve()
    bootloader = Path(args.bootloader).resolve()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "product": "nowacontrol_hydraulic_sensor",
        "version": args.version,
        "channel": args.channel,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": {
            "bootloader": file_info(bootloader),
            "application_hex": file_info(app_hex),
            "application_bin": file_info(app_bin),
        },
    }

    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
