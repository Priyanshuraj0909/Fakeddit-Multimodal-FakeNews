"""Dispatch a project pipeline; remaining arguments go to the selected CLI."""
import argparse
from pathlib import Path
import runpy
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
modules = {'text': 'ml.training.train_text', 'multimodal': 'ml.training.train_multimodal'}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("pipeline", choices=modules)
args = parser.parse_args(sys.argv[1:2])
rest = sys.argv[2:]
sys.argv = [modules[args.pipeline], *rest]
runpy.run_module(modules[args.pipeline], run_name="__main__")
