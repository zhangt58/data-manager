#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import math
import sys
import matplotlib.pyplot as plt
import pandas as pd

from datetime import datetime
from pathlib import Path
from typing import Union

from ._utils import (
    read_path,
    group_datafiles
)
from ._data import (
    read_data,
    plot
)
from ._tk import FigureWindow
from ._viewer import main as run_viewer
from ._log import logger


LOWER_LEFT_CORNER = u"\N{BOX DRAWINGS LIGHT UP AND RIGHT}"


def merge_tool(call_as_subtool: bool = False, prog: str = None):
    """ Merge the separated '.h5' files for each group/device into one on the MPS fault ID.
    """
    parser = argparse.ArgumentParser(
                prog=prog,
                description="Merge the BCM/BPM datasets into one file by the MPS fault ID. "
                            "It iterates the .h5' files recursively under the *data_dir*.")
    parser.add_argument("data_dir", default=None, type=str, nargs='?',
                        help="The directory path of the folder for the original '.h5' files.")
    parser.add_argument("out_dir", default=None, type=str, nargs='?',
                        help="The directory path of the folder for the merged files.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Overwrite the existing merged data files.")
    parser.add_argument("--csv-report", dest="csv_report",
                        help="The CSV filepath for writing the processed event report.")
    parser.add_argument("--log-level", dest="log_level", type=str, default="INFO",
                        help="Set the log level, DEBUG, INFO, WARNING, ERROR, CRITICAL")

    if call_as_subtool:
        args = parser.parse_args(sys.argv[2:])
    else:
        args = parser.parse_args(sys.argv[1:])

    logger.setLevel(args.log_level)

    if args.data_dir is None:
        logger.warning("The directory path of the original data files must be provided.")
        parser.print_help()
        sys.exit(1)

    if args.out_dir is None:
        logger.warning("The directory path for the merged files must be provided.")
        parser.print_help()
        sys.exit(1)

    df_evts = read_path(Path(args.data_dir))

    if args.csv_report is not None:
        if Path(args.csv_report).is_file():
            logger.debug(f"Exported table of events info to {args.csv_report} (overwritten)")
        else:
            logger.info(f"Exported table of events info to {args.csv_report}")
        df_evts.to_csv(args.csv_report)

    for i, (ftid, grp) in enumerate(df_evts.groupby(df_evts.index)):
        try:
            out_filepath = group_datafiles(ftid, grp, args.out_dir, args.overwrite)
        except Exception as e:
            logger.warning(f"Error processing {grp.shape[0]} files on MPS fault ID {ftid}: {e}")
        else:
            if out_filepath is None:
                logger.debug(f"Skipped merging {grp.shape[0]} file on MPS fault ID {ftid}")
            else:
                logger.info(f"Merged {grp.shape[0]} files on MPS fault ID {ftid}")


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
    parser.add_argument("--exclude-from", dest="exclude_file",
                        help="The file contains lines of filenames to exclude processing")
    parser.add_argument("--log-level", dest="log_level", type=str, default="INFO",
                        help="Set the log level, DEBUG, INFO, WARNING, ERROR, CRITICAL")

    if call_as_subtool:
        args = parser.parse_args(sys.argv[2:])
    else:
        args = parser.parse_args(sys.argv[1:])

    logger.setLevel(args.log_level)

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

    # The list of file names to exclude from processing
    exclude_filenames = []
    if args.exclude_file is not None:
        for line in open(args.exclude_file, "r"):
            if line.startswith("#"):
                continue
            exclude_filenames.append(line.strip())

    data_filepaths = sorted(set(args.data_filepath))
    for pth_s in data_filepaths:
        pth = Path(pth_s)
        if pth.name in exclude_filenames:
            logger.debug(f"Exclude {pth}")
            continue
        pth_name_0 = pth.name.rsplit('.', 1)[0]
        out_fn_no_ext = f"{pth_name_0}{args.suffix}"

        #
        out_filepaths = []
        for fmt in fmts:
            out_filepath = outdir_path.joinpath(f"{out_fn_no_ext}.{fmt}")
            if out_filepath.is_file() and not args.overwrite:
                logger.debug(f"Skip existing {out_filepath}, force with --overwrite")
            else:
                out_filepaths.append(out_filepath)
        #
        if not out_filepaths:
            continue

        df, t0_s = read_data(pth, t_range=(args.t1, args.t2))
        if df is None:
            logger.warning(f"Skip processing {pth}")
            continue
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
                logger.debug(f"Skip existing {out_filepath}, force with --overwrite")
        else:
            _export_fn_map[fmt](df, out_filepath)
            logger.info(f"{LOWER_LEFT_CORNER}As {out_filepath}")


def _export_df_as_mat(df: pd.DataFrame, out_filepath: Path):
    """ Export df as .mat file.
    """
    from scipy.io import savemat

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
    if 'BCM-FSCALE' in df.attrs:
        store.get_storer('BCM').attrs.fscale_json = json.dumps(df.attrs['BCM-FSCALE'])
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
    df_bcm_fscale = None
    if 'BCM-FSCALE' in df.attrs:
        df_bcm_fscale = pd.Series(df.attrs['BCM-FSCALE']).to_frame(name='value')

    with pd.ExcelWriter(out_filepath) as writer:
        df.to_excel(writer, sheet_name="data", index=False)
        if df_bcm_fscale is not None:
            df_bcm_fscale.to_excel(writer, sheet_name="BCM-FSCALE")


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
    parser.add_argument("--log-level", dest="log_level", type=str, default="INFO",
                        help="Set the log level, DEBUG, INFO, WARNING, ERROR, CRITICAL")
    parser.add_argument("-i", "--interactive", action="store_true", dest="user_mode",
                        help="Enter the user interactive mode, shortcuts image generation.")
    parser.add_argument("--grid", dest="fig_grid", default=None,
                        help="Pass nxm as the grid to layout the figures in interactive mode.")
    parser.add_argument("--nmax-figures", dest="max_nfigs", default=6, type=int,
                        help="The maximum number of figures to show in interactive mode.")
    parser.add_argument("--t1", dest="t1", type=int, default=None,
                       help="The relative start time against t0 in microseconds, "
                            "t0 is the time when trip event happens.")
    parser.add_argument("--t2", dest="t2", type=int, default=None,
                       help="The relative end time against t0 in microseconds, "
                            "(t1, t2) defines the range of data size trimmed from the merged (v0) "
                            "or v1 raw data; if none is defined, plot with the whole data.")
    parser.add_argument("--fig-dpi", dest="fig_dpi", type=int,
                        help="Override the figure DPI setting.")
    parser.add_argument("--fig-size", dest="fig_size", type=str,
                        help="Override the figure size setting, in wxh")
    parser.add_argument("--theme", dest="theme_name", type=str, default="arc",
                        help="The theme to style the UI, --list-themes to see options.")
    parser.add_argument("--list-themes", action="store_true",
                        help="List the supported UI themes.")
    parser.add_argument("--trip-info-file", dest="trip_info_file", type=str,
                        help="The .h5 file for the MPS MTCA trip info.")

    if call_as_subtool:
        args = parser.parse_args(sys.argv[2:])
    else:
        args = parser.parse_args(sys.argv[1:])

    logger.setLevel(args.log_level)

    if args.list_themes:
        import ttkthemes
        print(ttkthemes.THEMES)
        sys.exit(0)

    if not args.img_types:
        img_types = ("png", )
    else:
        img_types = set((t.lower() for t in args.img_types))

    t_range = None
    if args.t1 is not None and args.t2 is not None:
        t_range = (args.t1, args.t2)

    # shortcut image generation
    if args.user_mode:
        max_nfigs = args.max_nfigs
        n_data_filepaths = len(args.data_filepath)
        if n_data_filepaths > max_nfigs:
            logger.warning(f"Only process and show the first {max_nfigs} files ({n_data_filepaths}).")
            n_figs = max_nfigs
        else:
            n_figs = n_data_filepaths
        #
        fig_with_titles = []
        dbcm_dfs: list[pd.DataFrame] = []
        bcm_fscale_maps: list[dict] = []
        try:
            fig_w, fig_h = args.fig_size.split('x')
            fig_w = float(fig_w)
            fig_h = float(fig_h)
        except Exception:
            fig_w, fig_h = 12.4, 8
        for data_filepath in args.data_filepath[:n_figs]:
            _pth = Path(data_filepath)
            fig, df_dbcm, bcm_fscale_map = create_plot(_pth, args.is_opt, t_range,
                                                       fig_size=(fig_w, fig_h))
            if fig is None:
                continue
            fig.canvas.manager.set_window_title(f"Figure {_pth.name}")
            fig.tight_layout()
            fig_with_titles.append((fig, _pth.name))
            dbcm_dfs.append(df_dbcm)
            bcm_fscale_maps.append(bcm_fscale_map)

        fig_grid = args.fig_grid
        if fig_grid is None:
            nrow = math.floor(math.sqrt(n_figs))
            ncol = math.ceil(n_figs / nrow)
        else:
            nrow, ncol = [int(i) for i in fig_grid.split("x")]
        logger.debug("Plot user mode...")
        logger.debug(f"Invoking FigureWindow with {args.theme_name}")
        _app = FigureWindow(fig_with_titles,
                            "DM-Wave: Visualizing the Post-Mortem Data Interactively",
                            (nrow, ncol),
                            notes=f"[{datetime.now().isoformat()[:-3]}] "
                                  f"Generated with the command: {' '.join(sys.argv)}",
                            fig_dpi=args.fig_dpi, theme_name=args.theme_name,
                            dbcm_dfs=dbcm_dfs, bcm_fscale_maps=bcm_fscale_maps,
                            trip_info_file=args.trip_info_file)
        _app.mainloop()
        sys.exit(0)

    # otherwise generating images
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
        gen_figure(pth, img_types, img_outdir_path, is_opt=args.is_opt,
                   t_range=t_range, overwrite=args.overwrite)


def view_tool(call_as_subtool: bool = True, prog: str = None):
    """ Launch the GUI app to view MPS faults and the waveform data.
    """
    parser = argparse.ArgumentParser(
                prog=prog,
                description="Launch the GUI app for view the data along with MPS fault events.")
    parser.add_argument("mps_faults_file", type=str, default=None, nargs='?',
                        help="The filepath of the MPS faults event data.")
    parser.add_argument("images_dir", type=str, default=None, nargs='?',
                        help="The directory path of the processed images.")
    parser.add_argument("--trip-info-file", dest="trip_info_file", type=str,
                        help="The .h5 file for the MPS MTCA trip info.")
    parser.add_argument("--event-filter-file", dest="event_filter_file", type=str,
                        help="Exclude the defined MPS fault events by type, one Type per line.")
    parser.add_argument("--data-dir", action="append", dest="data_dirs",
                        help="The directory path for either the optimized, merged or raw data files.")
    parser.add_argument("--log-level", dest="log_level", type=str, default="INFO",
                        help="Set the log level, DEBUG, INFO, WARNING, ERROR, CRITICAL")
    parser.add_argument("--fig-dpi", dest="fig_dpi", type=int,
                        help="Override the figure DPI setting in interactive mode.")
    parser.add_argument("--fig-size", dest="fig_size", type=str,
                        help="Override the figure size setting, in wxh")
    parser.add_argument("--column-widths", dest="col_widths", type=json.loads, default="{}",
                        help="JSON string for the column widths of the tree view.")
    parser.add_argument("--geometry", dest="geometry", type=str, default="1600x1200",
                        help="The initial window size of the GUI.")
    parser.add_argument("--theme", dest="theme_name", type=str, default="arc",
                        help="The theme to style the UI, --list-themes to see options.")
    parser.add_argument("--list-themes", action="store_true",
                        help="List the supported UI themes.")
    parser.add_argument("--icon", dest="icon_path",
                        help="Set the icon.")

    args = parser.parse_args(sys.argv[2:])
    logger.setLevel(args.log_level)
    if args.list_themes:
        import ttkthemes
        print(ttkthemes.THEMES)
        sys.exit(0)
    if args.mps_faults_file is None or args.images_dir is None:
        logger.error("MPS faults file and image directory must be defined.")
        sys.exit(1)
    run_viewer(args.mps_faults_file, args.trip_info_file, args.event_filter_file,
               args.images_dir, args.data_dirs,
               args.geometry, args.fig_dpi, args.fig_size,
               args.theme_name,
               args.icon_path, **args.col_widths)


def gen_figure(data_filepath: Path, figure_types: list[str],
               out_dirpath: Path = None, is_opt: bool = False,
               t_range: Union[None, tuple[int, int]] = None,
               overwrite: bool = False):
    # is_opt: If set, work with the converted data file
    # otherwise, work with the merged file v0 or the new v1 format raw file.

    if out_dirpath is None:
        out_dirpath = data_filepath.parent

    filename = data_filepath.name
    img_outpaths = []
    for typ in figure_types:
        img_outpath = out_dirpath.joinpath(filename.replace(".h5", f".{typ}"))
        if img_outpath.is_file() and not overwrite:
            logger.debug(f"{LOWER_LEFT_CORNER}Skip existing {img_outpath}, force with --overwrite")
        else:
            img_outpaths.append(img_outpath)

    if not img_outpaths:
        return

    df, t0_s = read_data(data_filepath, t_range, is_opt)
    if df is None:
        logger.warning(f"Skip processing {data_filepath}")
        return
    #
    logger.info(f"Generating figure {data_filepath}...")
    fig = plot(df, t0_s, filename)
    fig.tight_layout()
    for img_outpath in img_outpaths:
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


def create_plot(data_filepath: Path, is_opt: bool = False,
                t_range: Union[None, tuple[int, int]] = None,
                fig_size: Union[tuple[float, float], None] = None):
    """ Create the matplotlib figure object.
    """
    df, t0_s = read_data(data_filepath, t_range, is_opt)
    if df is None:
        return None, None
    # raw DBCM data:
    df_dbcm = df[[c for c in df.columns if c.startswith('DBCM')]]
    bcm_fscale_map = df.attrs.get('BCM-FSCALE', None)
    return plot(df, t0_s, data_filepath.name, figsize=fig_size), df_dbcm, bcm_fscale_map


if __name__ == "__main__":
    merge_tool()
    # plot_tool()
