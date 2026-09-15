"""Allow `python -m watchkeeper_pipeline [stage...]`."""
import sys
from . import main

if __name__ == "__main__":
    main(sys.argv[1:])
