import sys
from setuptools import setup

# Delay pkg_resources import to avoid build errors in Python 3.12
try:
   import pkg_resources
   from pkg_resources import VersionConflict, require
   try:
       require("setuptools>=38.3")
   except VersionConflict:
       print("Error: version of setuptools is too old (<38.3)!")
       sys.exit(1)
except ModuleNotFoundError:
   # Skip check if pkg_resources is not yet installed
   pass

if __name__ == "__main__":
   setup()
