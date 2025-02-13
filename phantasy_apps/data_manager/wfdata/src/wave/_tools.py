#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import logging
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from scipy.io import savemat

from ._utils import read_path, group_datafiles
from ._data import read_data, plot

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] - %(levelname)s - %(message)s")
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

LOWER_LEFT_CORNER = u"\N{BOX DRAWINGS LIGHT UP AND RIGHT}"


def merge_tool(call_as_subtool: bool = False, prog: str = None):
    """ Merge the separated .h5 files for each group/device into one on the MPS fault ID.
    """
    parser = argparse.ArgumentParser(
                prog=prog,
                description="Merge the BCM/BPM datasets into one file by the MPS fault ID.")
    parser.add_argument("data_dir", default=None, type=str, nargs='?',
                        help="The directory path of the folder for the original .h5 files.")
    parser.add_argument("out_dir", default=None, type=str, nargs='?',
                        help="The directory path of the folder for the merged files.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Overwrite the existing merged data files.")
    parser.add_argument("--csv-report", dest="csv_report",
                        help="The CSV filepath for writing the processed event report.")

    if call_as_subtool:
        args = parser.parse_args(sys.argv[2:])
    else:
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
        out_filepath = group_datafiles(ftid, grp, args.out_dir, args.overwrite)
        logger.info(f"Merged {grp.shape[0]} files on MPS fault ID {ftid}...")

    if args.csv_report is not None:
        df_evts.to_csv(args.csv_report)
        logger.info(f"Exported table of events info to {args.csv_report}")


def convert_tool(call_as_subtool: bool = False, prog: str = None):
    """ Convert the data files to other formats.
    """
    _suppored_fmts = ('mat', 'h5', 'csv', 'xlsx')
    parser = argparse.ArgumentParser(
                prog=prog,
                description="Convert the merged HDF files to other formats, the exported "
                            "filename is suffixed with '_opt' by default.")
    parser.add_argument("data_filepath", default=None, nargs='+',
                        help="The filepath for the merged datasets, "
                             "Support passing multiple paths by Unix wildcards.")
    parser.add_argument("--fmt", action="append", dest="fmts",
                        help="The output data file format, pass multiple times for "
                             f"multi-format; supported formats: {', '.join(_suppored_fmts)}, "
                             "defaults to 'mat'.")
    parser.add_argument("--t1", dest="t1", type=int, default=-800,
                       help="The relative start time against t0 in microseconds, "
                            "t0 is the time when trip event happens.")
    parser.add_argument("--t2", dest="t2", type=int, default=400,
                       help="The relative end time against t0 in microseconds, "
                            "(t1, t2) defines the range of actual size of data exported.")
    parser.add_argument("--outdir", dest="outdir",
                        help="The directory for the exported files.")
    parser.add_argument("--suffix", dest="suffix", default="_opt",
                        help="The string suffix to the export filename.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Overwrite the existing exported files.")

    if call_as_subtool:
        args = parser.parse_args(sys.argv[2:])
    else:
        args = parser.parse_args(sys.argv[1:])

    if args.outdir is None:
        logger.warning("Output directory must be defined through --outdir.")
        parser.print_help()
        sys.exit(1)

    if args.fmts is None:
        fmts = ("mat", )
    else:
        fmts = sorted(set((i.lower() for i in args.fmts)))

    # check formats:
    for i in fmts:
        if i.lower() not in _suppored_fmts:
            logger.warning(f"{i} is not one of the supported {_suppored_fmts}")
            sys.exit(1)

    outdir_path = Path(args.outdir)
    if not outdir_path.is_dir():
        outdir_path.mkdir(parents=True)
        logger.info(f"Created output directory: {outdir_path}")

    data_filepaths = sorted(set(args.data_filepath))
    for pth_s in data_filepaths:
        pth = Path(pth_s)
        df, t0_s = read_data(pth, t_range=(args.t1, args.t2))
        if df is None:
            logger.warning(f"Skip processing {pth}")
            continue
        pth_name_0 = pth.name.rsplit('.', 1)[0]
        out_fn_no_ext = f"{pth_name_0}{args.suffix}"
        logger.info(f"Exporting {pth}...")
        export_df(df, outdir_path, out_fn_no_ext, fmts, args.overwrite)


def export_df(df: pd.DataFrame, outdir: Path, out_filename: str,
              out_formats: list[str], overwrite: bool = False):
    """ Export the dataframe to *outdir* directory as the given formats.
    """
    _export_fn_map = {
        'mat': _export_df_as_mat,
        'h5': _export_df_as_h5,
        'csv': _export_df_as_csv,
        'xlsx': _export_df_as_xlsx,
    }
    for fmt in out_formats:
        out_filepath = outdir.joinpath(f"{out_filename}.{fmt}")
        if out_filepath.is_file():
            if overwrite:
                _export_fn_map[fmt](df, out_filepath)
                logger.info(f"{LOWER_LEFT_CORNER}As {out_filepath} (overwritten)")
            else:
                logger.info(f"Skip existing {out_filepath}, force with --overwrite")
        else:
            _export_fn_map[fmt](df, out_filepath)
            logger.info(f"{LOWER_LEFT_CORNER}As {out_filepath}")


def _export_df_as_mat(df: pd.DataFrame, out_filepath: Path):
    """ Export df as .mat file.
    """
    # replace the "-" to "_" for the column names, as MATLAB struct does not support strings
    # with "-" as the keys.
    df = df.rename(lambda c: c.replace("-", "_"), axis=1)
    t_start: str = df.index[0].isoformat()
    t_zero: str = df[df.t_us == 0].index[0].isoformat()
    mat_data: dict = df.to_dict(orient="list")
    mat_data.update({'t_start': t_start, 't_zero': t_zero})
    #
    savemat(out_filepath, mat_data, do_compression=True)


def _export_df_as_h5(df: pd.DataFrame, out_filepath: Path):
    """ Export df as .h5 file.
    """
    df_t_us = df['t_us']
    df_bcm = df[[c for c in df.columns if 'BCM' in c]]
    df_bpm_mag = df[[c for c in df.columns if 'MAG' in c]]
    df_bpm_pha = df[[c for c in df.columns if 'PHA' in c]]
    store = pd.HDFStore(out_filepath, mode="a", complevel=9, complib="bzip2")
    for k, dfk in zip(('TimeWindow', 'BCM', 'BPM_MAG', 'BPM_PHA'),
                      (df_t_us, df_bcm, df_bpm_mag, df_bpm_pha)):
        store.put(k, dfk)
    t_start: str = df.index[0].isoformat()
    t_zero: str = df[df.t_us == 0].index[0].isoformat()
    store.get_storer('TimeWindow').attrs.t_start = t_start
    store.get_storer('TimeWindow').attrs.t_zero = t_zero
    store.close()


def _export_df_as_csv(df: pd.DataFrame, out_filepath: Path):
    """ Export df as .csv file.
    """
    df.to_csv(out_filepath)


def _export_df_as_xlsx(df: pd.DataFrame, out_filepath: Path):
    """ Export df as .xlsx file.
    """
    # Save time index as two columns: ts_second, ts_microsec
    #
    df[["time_sec", "time_usec"]] = \
        df.index.map(lambda i: (int(i.timestamp() * 1e6 // 1e6),
                                int(i.timestamp() * 1e6 % 1e6))).to_list()
    df.to_excel(out_filepath, index=False)


def plot_tool(call_as_subtool: bool = False, prog: str = None):
    """ Plot the merged dataset to images.
    """
    parser = argparse.ArgumentParser(
            prog=prog,
            description="Generate images from the merged BCM/BPM waveform dataset files; "
                        "Pass flag -opt if working with the optimized dataset files (see convert tool).")
    parser.add_argument("data_filepath", default=None, nargs='+',
                        help="The filepath for the merged datasets (.h5 files), "
                             "Support passing multiple paths by Unix wildcards.")
    parser.add_argument("--img-type", dest="img_types", action="append",
                        help="The image type to output the figure from the merged data file, "
                             "pass one with --img-type.")
    parser.add_argument("--img-outdir", dest="img_outdir",
                        help="The directory for the generated image files, defaults to "
                             "the parent directory of the data file.")
    parser.add_argument("-opt", action="store_true", dest="is_opt",
                        help="If the data_filepaths are optimized .h5 files.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Overwrite the existing image files.")

    if call_as_subtool:
        args = parser.parse_args(sys.argv[2:])
    else:
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
        logger.info(f"Generating figure {pth}...")
        gen_figure(pth, img_types, img_outdir_path, is_opt=args.is_opt,
                   overwrite=args.overwrite)


def gen_figure(data_filepath: Path, figure_types: list[str],
               out_dirpath: Path = None, is_opt: bool = False,
               overwrite: bool = False):

    if out_dirpath is None:
        out_dirpath = data_filepath.parent

    if is_opt:
        store = pd.HDFStore(data_filepath)
        t0_s = store.get_storer('TimeWindow').attrs.t_zero
        df = pd.concat([store[k] for k in store.keys()], axis=1)
        store.close()
    else:
        df, t0_s = read_data(data_filepath)
    if df is None:
        logger.warning(f"Skip processing {data_filepath}")
        return
    filename = data_filepath.name
    fig = plot(df, t0_s, filename)
    fig.tight_layout()
    for typ in figure_types:
        img_outpath = out_dirpath.joinpath(filename.replace(".h5", f".{typ}"))
        if img_outpath.is_file():
            if overwrite:
                fig.savefig(img_outpath)
                logger.info(f"{LOWER_LEFT_CORNER}As {img_outpath} (overwritten)")
            else:
                logger.info(f"{LOWER_LEFT_CORNER}Skip existing {img_outpath}, force with --overwrite")
        else:
            fig.savefig(img_outpath)
            logger.info(f"{LOWER_LEFT_CORNER}As {img_outpath}")
    #
    plt.close(fig)


if __name__ == "__main__":
    merge_tool()
    # plot_tool()
