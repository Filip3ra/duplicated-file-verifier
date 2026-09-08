"""PyInstaller entry for the windowed GUI."""

from multiprocessing import freeze_support

from duplicate_verifier.gui import run_app_main

if __name__ == "__main__":
    freeze_support()
    run_app_main()
