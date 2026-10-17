"""python -m chuni <AXXX dir | Option dir> <output dir>"""
import sys

from chuni.parse import process_directory

process_directory(sys.argv[1], sys.argv[2])
