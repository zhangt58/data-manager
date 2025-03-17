#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('tkagg')

import sys
from ._tools import (
    convert_tool,
    merge_tool,
    plot_tool,
    view_tool,
)
from ._ver import _version


__authors__ = "Tong Zhang"
__copyright__ = "(c) 2025, Facility for Rare Isotope Beams," \
                " Michigan State University"
__contact__ = "Tong Zhang <zhangt@frib.msu.edu>"
__version__ = _version
__title__ = "DataManager: Manage the Accelerator Data"

TOOLS = {
    'merge': merge_tool,
    'plot': plot_tool,
    'convert': convert_tool,
    'view': view_tool
}

_help_msg = """Usage: wf-wave [-h] [-v] {merge,plot,convert} ...

The main tool for processing the post-mortem BPM/BCM waveform data files.

On each MPS MTCA06 trip event, the waveform data is captured and stored as HDF5 files
(referred as raw files) by another application. For v0 formatted files, use `merge` tool
to merge the raw files to a single file based on the MPS fault ID. Use `convert` and `plot`
tool to convert the merged or v1 formatted raw files to other formats, only clip the data
around the trip region; generate the images in various types with `plot` tool.

`view` tool provides the GUI and interactively view the data in images.

Options:
  -h   Show this help message and exit
  -v   Print out version info

Valid tools:
  merge      Merge the raw (v0) BCM/BPM datasets into one by the MPS fault ID
  convert    Convert the merged or raw (v1) HDF5 files to other formats
  plot       Generate images from the converted BCM/BPM waveform dataset files
  view       GUI app for view data and images
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
