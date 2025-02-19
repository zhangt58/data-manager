#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import sys

from ._tools import (
    convert_tool,
    merge_tool,
    plot_tool
)

from ._utils import (
    group_datafiles,
    read_path,
)

from ._data import (
    plot,
    read_data,
)

__authors__ = "Tong Zhang"
__copyright__ = "(c) 2025, Facility for Rare Isotope Beams," \
                " Michigan State University"
__contact__ = "Tong Zhang <zhangt@frib.msu.edu>"
__version__ = '0.3.2'
__title__ = "DataManager: Manage the Accelerator Data"


TOOLS = {
    'merge': merge_tool,
    'plot': plot_tool,
    'convert': convert_tool
}


_help_msg = """Usage: wf-wave [-h] [-v] {merge,plot,convert} ...

The main tool for BCM/BPM waveform data.

Options:
  -h   Show this help message and exit
  -v   Print out version info

Valid tools:
  merge      Merge the raw BCM/BPM datasets into one by the MPS fault ID
  plot       Generate images from the merged BCM/BPM waveform dataset files
  convert    Convert the merged HDF files to other formats
"""

def main():
    """ The main command for other tools
    """
    if len(sys.argv) < 2:
        print(_help_msg, file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "-h":
        print(_help_msg)
        sys.exit(0)

    if sys.argv[1] == "-v":
        print(f"{__title__}\nVersion: {__version__}")
        sys.exit(0)

    tool_name = sys.argv[1].strip().lower()
    if tool_name not in TOOLS:
        print(f"{tool_name} is not supported.", file=sys.stderr)
        sys.exit(1)

    #
    TOOLS[tool_name](call_as_subtool=True, prog=f"wf-wave {tool_name}")
