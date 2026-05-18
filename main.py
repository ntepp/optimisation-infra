"""
CLI entry point — thin wrapper around the inbound CLI adapter.

Usage:
  python main.py --mode single --input docs/rapport.json --index 0
  python main.py --mode batch  --input docs/rapport.json --window 120
  python main.py --mode batch  --input docs/rapport.json --all
  cat docs/rapport.json | python main.py --source stdin --window 60
  python main.py --source inline --json '{"timestamp":"...","cpu_usage":92,...}'
"""
from dotenv import load_dotenv

load_dotenv()

from src.adapters.inbound.cli import run_cli


if __name__ == "__main__":
    run_cli()
