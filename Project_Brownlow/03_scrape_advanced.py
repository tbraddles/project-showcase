"""Step 3: download Champion-style advanced stats."""

import sys

from brownlow.cli import main

if __name__ == "__main__":
    main(["scrape-advanced", *sys.argv[1:]])
