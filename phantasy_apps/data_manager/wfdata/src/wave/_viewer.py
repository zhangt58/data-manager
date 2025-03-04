#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
from pathlib import Path
from functools import partial
from typing import Union

from ._tk import configure_styles
from ._log import logger
from ._ver import _version

LOWER_LEFT_CORNER = u"\N{BOX DRAWINGS LIGHT UP AND RIGHT}"
MU_GREEK = u"\N{GREEK SMALL LETTER MU}"
DEFAULT_INFO_STRING = f"DM-Wave Viewer v{_version}"


class MainWindow(tk.Tk):

    def __init__(self, csv_file: str, trip_info_file: str, imags_dir: str,
                 data_dirs: list[str], fig_dpi: Union[int, None] = None,
                 column_widths: dict = None):
        super().__init__()

        # styles
        configure_styles(self)

        #  window title
        self.title("Post-mortem Data Viewer on MPS Faults")

        # read the data for the table
        self.csv_file = csv_file
        self.trip_info_file = trip_info_file
        self.data = self.read_data()
        #
        self.images_dirpath = Path(imags_dir)
        self.data_dirs: list[Path] = [Path(d) for d in data_dirs]
        self.column_widths = {} if column_widths is None else column_widths
        self.fig_dpi= fig_dpi

        #
        self.info_var = tk.StringVar()
        self.info_var.set(DEFAULT_INFO_STRING)
        self.preview_info_var = tk.StringVar()
        self.preview_info_var.set("")
        self.nrecords_var = tk.StringVar()
        self.nrecords_var.set(f"{0:>4d} in total")

        # | ----- | ------- |
        # | Table | preview |
        # | ----- | ------- |
        #
        self.create_table_panel()
        self.create_preview_panel()

    def read_data(self, filter: Union[str, None] = None) -> pd.DataFrame:
        """ Read a list or rows data from *csv_file*.
        # filter the "Description" column: MTCA06
        # filter the "T Window" column: 150us
        """
        df = pd.read_csv(self.csv_file, delimiter=";")
        # merge the trip info if available
        if self.trip_info_file is not None:
            _df_info = pd.read_hdf(self.trip_info_file)[
                    ["devices", "t window", "threshold", "ID"]]
            df = pd.merge(df, _df_info.rename(columns={
                    "ID": "Fault_ID",
                    "devices": "Devices",
                    "t window": "T Window",
                    "threshold": "Threshold",
                    }), on="Fault_ID", how="left")
        if filter == "MTCA06":
            df = df[df["Description"]=="MTCA06"].reset_index(drop=True)
        elif filter == "150us":
            if "T Window" in df:
                df = df[df["T Window"].astype(str).str.contains(
                        "Diff 150[^0]s", regex=True)].reset_index(drop=True)
                self.info_var.set(DEFAULT_INFO_STRING)
            else:
                self.info_var.set("MTCA trip info is not available!")
        return df

    def create_table_panel(self):
        """ Create the table for MPS faults data
        """
        #
        # | tree frame
        # | bottom frame
        #
        left_panel = ttk.Frame(self)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.left_panel = left_panel

        tree_frame = ttk.Frame(left_panel)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(tree_frame,
                            columns=self.data.columns.to_list(),
                            show="headings", selectmode="browse")
        self.tree = tree

        # scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=v_scroll.set)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        #
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # column headers
        for i, header in enumerate(self.data.columns):
            tree.heading(i, text=header)
            col_w = self.column_widths.get(header, None)
            if col_w is not None:
                logger.warning(f"Set {header} width to {col_w}")
                tree.column(header, width=col_w)

        # tag-wised style
        tree.tag_configure("mtca06", foreground="black")
        tree.tag_configure("non-mtca06", foreground="gray")

        tree.bind("<<TreeviewSelect>>", self.on_select_row)

        # table data
        self.present_table_data()

        # The widgets below the tree_frame
        # frame1
        # |- [All] [MTCA06] Event on Preview   [Open Raw] [Open Opt]
        # frame2
        # |- Info: xxxx
        bottom_frame1 = ttk.Frame(left_panel)
        bottom_frame1.pack(fill=tk.X, padx=10, pady=10)

        # all
        reload_all_btn = ttk.Button(bottom_frame1, text="Reload All",
                                    command=partial(self.on_reload, None))
        reload_all_btn.pack(side=tk.LEFT)
        # description = MTCA06
        reload_mtca_btn = ttk.Button(bottom_frame1, text="MTCA06",
                                     command=partial(self.on_reload, "MTCA06"))
        reload_mtca_btn.pack(side=tk.LEFT, padx=10)
        # T Window has 150us (need --trip-info-file)
        reload_fast_trip_btn = ttk.Button(bottom_frame1, text=f"Diff 150{MU_GREEK}s",
                                          command=partial(self.on_reload, f"150us"))
        reload_fast_trip_btn.pack(side=tk.LEFT, padx=10)
        #
        # total entries
        nrows_lbl = ttk.Label(bottom_frame1, textvariable=self.nrecords_var)
        nrows_lbl.pack(side=tk.LEFT, padx=10)
        #
        preview_info_lbl = ttk.Label(bottom_frame1, textvariable=self.preview_info_var)
        preview_info_lbl.pack(side=tk.LEFT, padx=10)
        self.preview_info_lbl = preview_info_lbl

        #
        open_btn = ttk.Button(bottom_frame1, text="Open Opt", command=partial(self.on_open, True))
        open_btn.pack(side=tk.RIGHT, padx=10)
        open1_btn = ttk.Button(bottom_frame1, text="Open Raw", command=partial(self.on_open, False))
        open1_btn.pack(side=tk.RIGHT, padx=10)

        #
        bottom_frame2 = ttk.Frame(left_panel)
        bottom_frame2.pack(side=tk.BOTTOM, fill=tk.X, pady=4)
        # info label
        info_lbl = ttk.Label(bottom_frame2, textvariable=self.info_var)
        info_lbl.pack(fill=tk.X, padx=10)
        self.info_lbl = info_lbl

    def create_preview_panel(self):
        self.preview_frame = ttk.Frame(self)
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10, pady=10)

        self.image_lbl = ttk.Label(self.preview_frame)
        self.image_lbl.pack(fill=tk.BOTH, expand=True)
        self.preview_image = None
        self.preview_img_filepath = None
        self.preview_img_ftid = None
        self.update_preview()

    def on_select_row(self, evt):
        _row = self.tree.focus()
        if _row:
            items = self.tree.item(_row, "values")
            # show the figure if available
            self.display_figure(items)
            logger.debug(f"Selected {_row}: {items}, {self.data.iloc[int(_row)]}")

    def on_reload(self, filter: Union[str, None] = None):
        """ Reload the MPS faults table.
        """
        self.refresh_table_data(filter)

    def on_open(self, is_opt: bool):
        # find the data files
        if self.preview_img_ftid is None:
            return

        data_path = self.find_data_path(self.preview_img_ftid, is_opt)
        if data_path is not None:
            # call plot tool
            cmdline = f"dm-wave plot -opt -i {data_path}" if is_opt else \
                      f"dm-wave plot -i {data_path}"
            if self.fig_dpi is not None:
                cmdline += f" --fig-dpi {self.fig_dpi}"
            _info_msg = "Opening the figure with the raw data" if not is_opt else \
                        "Opening the figure with the opt data"
            subprocess.Popen(cmdline, shell=True)

    def find_data_path(self, ftid: int, is_opt: bool = True) -> Path:
        glob_pattern = f"{ftid}_opt.h5" if is_opt else f"*{ftid}.h5"
        for d in self.data_dirs:
            for pth in d.rglob(glob_pattern):
                if pth.is_file():
                    return pth
        return None

    def find_image_path(self, ftid: int) -> Path:
        glob_pattern = f"*{ftid}_opt.png"
        for pth in self.images_dirpath.rglob(glob_pattern):
            if pth.is_file():
                return pth
        return None

    def update_preview(self):
        self.image_lbl.config(image=self.preview_image)
        self.image_lbl.config(text=self.preview_img_filepath)

    def display_figure(self, row):
        ftid: str = row[0]
        img_filepath = self.find_image_path(ftid)
        if img_filepath is not None:
            self.preview_image = PhotoImage(file=img_filepath)
            self.preview_img_filepath = img_filepath
            self.preview_img_ftid = int(ftid)
            self.update_preview()
            self.preview_info_var.set(f"Event on Preview: {self.preview_img_ftid}")
            self.info_var.set(DEFAULT_INFO_STRING)
        else:
            logger.warning(f"Not found the image for {ftid}")
            self.info_var.set(f"No image found for MPS fault ID {ftid}")

    def present_table_data(self):
        """ Present the data to the table.
        """
        for i, row in self.data.iterrows():
            if row["Description"] == "MTCA06":
                _tag = "mtac06"
            else:
                _tag = "non-mtca06"
            self.tree.insert("", tk.END, iid=i, values=row.to_list(), tags=(_tag, ))

        # post the total number of entries
        self.nrecords_var.set(f"{self.data.shape[0]:>4d} in total")

    def refresh_table_data(self, filter: Union[str, None] = None):
        """ Re-read the data and refresh the table.
        """
        self.data = self.read_data(filter)
        self.tree.delete(*self.tree.get_children())
        self.present_table_data()


def main(mps_faults_path: str, trip_info_file: str, images_dir: str, data_dirs: list[str],
         minsize: str = "1200x900", fig_dpi: Union[int, None] = None, **kws):
    app = MainWindow(mps_faults_path, trip_info_file, images_dir, data_dirs, fig_dpi,
                     column_widths=kws)
    w, h = minsize.split('x')
    app.minsize(width=w, height=h)
    app.mainloop()

