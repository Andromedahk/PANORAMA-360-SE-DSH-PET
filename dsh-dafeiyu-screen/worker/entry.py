"""Load our worker from a cached isolated Python without changing its _pth file."""
import pathlib, runpy, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
runpy.run_module('bridge', run_name='__main__')
