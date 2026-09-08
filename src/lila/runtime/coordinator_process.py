"""Dedicated coordinator process; managed by the user-session supervisor."""
import argparse
from pathlib import Path
from lila.runtime.service import Runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir",type=Path,required=True)
    args = parser.parse_args()
    runtime = Runtime(args.data_dir)
    if not runtime.start():
        return 2
    try:
        runtime.monitor()
    finally:
        runtime.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
