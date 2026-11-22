#!/usr/bin/env python3
"""
Classic-Mode Campus GLB Entrypoint (Single-Source Wrapper)

Delegates directly to `generate_campus_glb.py --variant classic` so Classic
(`*-classic.glb`) and Enhanced (`*.glb`) models always stay 100% geometrically
synchronized from a single procedural source, while Classic exports preserve
lossless FLOAT32 vertex positions via `optimize_glb.mjs --preserve-positions`
and eliminate back-to-back duplicate double-sided triangles & Z-fighting.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild Classic-mode campus GLB models")
    parser.add_argument(
        "--campus",
        choices=("west", "east", "all"),
        default="all",
        help="Which campus classic GLB to rebuild (default: all)",
    )
    args = parser.parse_args()
    gen_script = Path(__file__).resolve().parent / "generate_campus_glb.py"
    subprocess.run([sys.executable, str(gen_script), "--campus", args.campus, "--variant", "classic"], check=True)


if __name__ == "__main__":
    main()
