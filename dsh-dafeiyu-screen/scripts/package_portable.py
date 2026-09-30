"""Compatibility entry: build a thin package; dependencies download on demand."""
import argparse, pathlib, subprocess
p=argparse.ArgumentParser();p.add_argument('--output');a=p.parse_args()
args=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(pathlib.Path(__file__).with_name('package.ps1'))]
if a.output:args+=['-OutputDirectory',a.output]
subprocess.run(args,check=True)
