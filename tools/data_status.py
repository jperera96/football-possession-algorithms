"""Check the status of match assets and environment configuration.

Run:
    python tools/data_status.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from games import GAME, GAMES, SOURCES, DATA_DIR, asset_paths


def check_assets():
    print("=" * 60)
    print("Match Asset & Data Status Check")
    print("=" * 60)
    print(f"Target match: {GAME}")
    print(f"Configured data directory: {DATA_DIR}")
    print(f"Exists: {os.path.isdir(DATA_DIR)}")
    print("-" * 60)

    for source in ("tactical", "broadcast"):
        print(f"\nSource: {source.upper()} ({SOURCES[source]['n_video_frames']} frames)")
        paths = asset_paths(source=source)
        for asset, path in paths.items():
            exists = os.path.isfile(path)
            if exists:
                size_mb = os.path.getsize(path) / (1024 * 1024)
                status = f"PRESENT ({size_mb:,.1f} MB)"
            else:
                status = "MISSING"
            rel_path = os.path.relpath(path, ROOT)
            print(f"  {asset:<14} [{status:<18}] -> {rel_path}")

    print("\n" + "=" * 60)
    gt_path = os.path.join(ROOT, "evaluation", "gt", f"{GAME}_possession_gt_public.csv")
    gt_exists = os.path.isfile(gt_path)
    print(f"Public Ground Truth: {'PRESENT' if gt_exists else 'MISSING'} ({os.path.relpath(gt_path, ROOT)})")
    print("=" * 60)


if __name__ == "__main__":
    check_assets()
