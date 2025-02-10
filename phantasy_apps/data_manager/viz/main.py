#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import argparse
import sys
import logging
import matplotlib.pyplot as plt
from pathlib import Path

from _utils import read_path, group_datafiles
from _data import read_data, plot

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] - %(levelname)s - %(message)s")
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def merge_tool():
    """ Merge the separated .h5 files for each group/device into one on the MPS fault ID.
    """

    parser = argparse.ArgumentParser(
                description="Merge the BCM/BPM datasets into one file by the MPS fault ID.")
    parser.add_argument("data_dir", default=None, type=str, nargs='?',
                        help="The directory path of the folder of the original dataset files.")
    parser.add_argument("out_dir", default=None, type=str, nargs='?',
                        help="The directory path of the folder to keep the output files.")
    parser.add_argument("--override", action="store_true",
                        help="Override the existing merged data files.")
    parser.add_argument("--csvfile-table", dest="csvfile_table",
                        help="The CSV filepath for exporting the metadata table of the original "
                             "data files.")

    args = parser.parse_args(sys.argv[1:])

    if args.data_dir is None:
        logger.warning("The directory path of the original data files must be provided.")
        parser.print_help()
        sys.exit(1)

    if args.out_dir is None:
        logger.warning("The directory path for the merged files must be provided.")
        parser.print_help()
        sys.exit(1)

    df_evts = read_path(Path(args.data_dir))

    for i, (ftid, grp) in enumerate(df_evts.groupby(df_evts.index)):
        out_filepath = group_datafiles(ftid, grp, args.out_dir)
        logger.info(f"Merged {grp.shape[0]} files on MPS fault ID {ftid}...")
        # gen_figure(out_filepath, args.fig_types)
        if i == 9999:
            break
    if args.csvfile_table is not None:
        df_evts.to_csv(args.csvfile_table)
        logger.info(f"Exported table of events info to {args.csvfile_table}")


def plot_tool():
    """ Plot the merged dataset to images.
    """
    parser = argparse.ArgumentParser(
            description="Generate images from the merged BCM/BPM waveform dataset files.")
    parser.add_argument("data_filepath", default=None, nargs='+',
                        help="The filepath for the merged datasets.")
    parser.add_argument("--img-type", dest="img_types", action="append",
                        help="The image type to output the figure from the merged data file, "
                             "pass one with --img-type.")
    parser.add_argument("--img-outdir", dest="img_outdir",
                        help="The directory for the generated image files, defaults to "
                             "the parent directory of the data file.")

    args = parser.parse_args(sys.argv[1:])

    if not args.img_types:
        img_types = ("png", )
    else:
        img_types = set((t.lower() for t in args.img_types))

    data_filepaths = sorted(set(args.data_filepath))

    img_outdir_path = args.img_outdir
    if img_outdir_path is not None:
        img_outdir_path = Path(img_outdir_path)
        img_outdir_path.mkdir(exist_ok=True, parents=True)

    for pth_s in data_filepaths:
        pth = Path(pth_s)
        if not pth.is_file():
            logger.warning(f"Not exists: {pth}")
            continue
        gen_figure(pth, img_types, img_outdir_path)



def gen_figure(data_filepath: Path, figure_types: list[str],
               out_dirpath: Path = None):

    if out_dirpath is None:
        out_dirpath = data_filepath.parent

    df, t0_s = read_data(data_filepath)
    if df is None:
        logger.warning(f"Skip processing {data_filepath}")
        return
    filename = data_filepath.name
    fig = plot(df, t0_s, filename)
    fig.tight_layout()
    for typ in figure_types:
        img_outpath = out_dirpath.joinpath(filename.replace(".h5", f".{typ}"))
        fig.savefig(img_outpath)
        logger.info(f"Generated {img_outpath}")
    #
    plt.close(fig)


if __name__ == "__main__":
    merge_tool()
    # plot_tool()
