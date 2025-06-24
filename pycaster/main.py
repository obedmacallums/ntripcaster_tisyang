import argparse
import trio
import sys
import os

# Add the parent directory to sys.path so we can import pycaster
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pycaster.config import load_config
    from pycaster.server import run_server
except ImportError:
    # If running directly, try relative imports
    from config import load_config
    from server import run_server


def main():
    parser = argparse.ArgumentParser(description="Simple NTRIP caster written in Python/Trio")
    parser.add_argument('config', nargs='?', default='ntripcaster.json', help='Path to config file')
    args = parser.parse_args()
    cfg = load_config(args.config)
    trio.run(run_server, cfg)


if __name__ == '__main__':
    main()
