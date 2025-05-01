import sys
import os

# Adjust sys.path to include the parent directory of 'src'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# This file is used to configure pytest and adjust the sys.path for all tests
