import argparse
import trio
from .config import load_config
from .server import run_server


def main():
    parser = argparse.ArgumentParser(description="Simple NTRIP caster written in Python/Trio")
    parser.add_argument('config', nargs='?', default='ntripcaster.json', help='Path to config file')
    args = parser.parse_args()
    cfg = load_config(args.config)
    trio.run(run_server, cfg)


if __name__ == '__main__':
    main()
