"""Step 2: download player stats for the configured season."""

import sys

from brownlow.cli import main

if __name__ == "__main__":
    main(["scrape-players", *sys.argv[1:]])
