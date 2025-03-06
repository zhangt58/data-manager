#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from functools import partial
from typing import Union
from PIL import Image, ImageTk

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

        # screen resolution
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()

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
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        self.main_frame = main_frame
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
        # | main tree frame
        # | trip-info tree frame
        # | bottom frame
        #
        left_panel = ttk.Frame(self.main_frame,
                               width=min(800, self.screen_width // 3))
        logger.info(f"Set the left panel width < {min(800, self.screen_width // 3)}px")
        left_panel.grid(row=0, column=0, sticky="nsw")
        self.left_panel = left_panel

        tree_frame = ttk.Frame(left_panel)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree_frame.pack_propagate(False)
        tree = ttk.Treeview(tree_frame,
                            columns=self.data.columns.to_list(),
                            show="headings", selectmode="browse")
        self.tree = tree

        # scrollbars
        h_scroll = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=tree.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        v_scroll = tk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
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
        # |- [All] [MTCA06] Event on Preview
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
        bottom_frame2 = ttk.Frame(left_panel)
        bottom_frame2.pack(side=tk.BOTTOM, fill=tk.X, pady=4)
        # info label
        info_lbl = ttk.Label(bottom_frame2, textvariable=self.info_var)
        info_lbl.pack(fill=tk.X, padx=10)
        self.info_lbl = info_lbl

    def create_preview_panel(self):
        # right panel
        # |- image label
        # |- [fit]   [Open Raw] [Open Opt]
        self.right_panel = ttk.Frame(self.main_frame, borderwidth=2)
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        self.right_panel.rowconfigure(0, weight=1)
        self.right_panel.rowconfigure(1, weight=0)
        self.right_panel.columnconfigure(0, weight=1)
        # image
        img_frame = tk.Frame(self.right_panel, bg="lightgray")
        img_frame.grid(row=0, column=0, sticky="nsew")

        _font = tk.font.nametofont("TkTextFont")
        self.image_lbl = ttk.Label(img_frame, anchor=tk.CENTER,
                                   font=(_font.actual()['family'],
                                         int(_font.actual()['size'] * 1.5)))
        self.image_lbl.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.loaded_image = None  # the loaded image from a png file.
        self.loaded_image_tk = None  # the image put into a tk label.
        self.loaded_img_filepath = None
        self.loaded_image_ftid = None
        self.loaded_image_var = tk.StringVar()
        self.loaded_image_var.trace_add("write", self.update_preview)
        # initial image label
        self.image_lbl.config(text="Select an event to preview the image")

        # control frame
        ctrl_frame = tk.Frame(self.right_panel)
        ctrl_frame.grid(row=1, column=0, sticky="ew")
        fit_btn = ttk.Button(ctrl_frame, text="Fit Image", command=self.on_fit_image)
        fit_btn.pack(side=tk.LEFT, padx=5)
        #
        open_btn = ttk.Button(ctrl_frame, text="Open Opt", command=partial(self.on_open, True))
        open_btn.pack(side=tk.RIGHT, padx=5)
        open1_btn = ttk.Button(ctrl_frame, text="Open Raw", command=partial(self.on_open, False))
        open1_btn.pack(side=tk.RIGHT, padx=10)

    def on_fit_image(self):
        """ Fit the size of image to the right panel.
        """
        w = self.right_panel.winfo_width()
        h = self.right_panel.winfo_height()
        if self.loaded_image is not None:
            w0, h0 = self.loaded_image.width, self.loaded_image.height
            new_w = w  # min(w0, w)
            new_h = int(new_w * h0 / w0)
            logger.debug(f"Resizing image frame to: {new_w}x{new_h}")
            _loaded_image_resized = self.loaded_image.resize((new_w, new_h),
                                                             Image.Resampling.LANCZOS)
            self.loaded_image_tk = ImageTk.PhotoImage(_loaded_image_resized)
            self.image_lbl.config(image=self.loaded_image_tk)

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
        if self.loaded_image_ftid is None:
            return

        data_path = self.find_data_path(self.loaded_image_ftid, is_opt)
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

    def update_preview(self, *args):
        self.loaded_img_filepath = img_filepath = self.loaded_image_var.get()
        self.loaded_image = Image.open(img_filepath)
        self.loaded_image_tk = ImageTk.PhotoImage(self.loaded_image)
        self.image_lbl.config(image=self.loaded_image_tk)
        self.image_lbl.config(text=self.loaded_img_filepath)
        self.on_fit_image()

    def display_figure(self, row):
        ftid: str = row[0]
        img_filepath = self.find_image_path(ftid)
        if img_filepath is not None:
            self.loaded_image_ftid = int(ftid)
            self.loaded_image_var.set(img_filepath)
            self.preview_info_var.set(f"Event on Preview: {ftid}")
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
         geometry: str = "1600x1200", fig_dpi: Union[int, None] = None, **kws):
    app = MainWindow(mps_faults_path, trip_info_file, images_dir, data_dirs, fig_dpi,
                     column_widths=kws)
    app.geometry(geometry)
    w, h = geometry.split("x")
    app.minsize(width=w, height=h)
    logger.info(f"Set the initial size {geometry}")
    app.mainloop()

