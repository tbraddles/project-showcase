"""Step 5: train the model and export Brownlow predictions."""

import sys

from brownlow.cli import main

if __name__ == "__main__":
    main(["predict", *sys.argv[1:]])
