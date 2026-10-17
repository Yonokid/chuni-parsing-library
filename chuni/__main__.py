"""python -m chuni <AXXX dir | Option dir> <output dir> [base A000 dir]

The base A000 supplies assets (audio, banners, ...) the given folders lack; it defaults to the
game's App/data/A000 for an Option dir. Pass it when that A000 is itself only a patch.
"""
import sys

from chuni.parse import process_directory

process_directory(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
