from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Run the GUI by default, or delegate to the CLI when arguments are present."""
    args = sys.argv[1:] if argv is None else argv
    if args:
        from ascii_foundry.cli.main import main as cli_main

        return cli_main(args)

    try:
        from ascii_foundry.app import run
    except ImportError as exc:
        print("PySide6 is required for the desktop app. Install with: pip install -e .[gui]")
        print(f"Import error: {exc}")
        return 2

    return run()

