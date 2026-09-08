"""PyInstaller entry for the console CLI."""

from multiprocessing import freeze_support

from duplicate_verifier.cli import main

if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
