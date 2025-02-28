#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
from pathlib import Path
from functools import partial

from ._tk import configure_styles
from ._log import logger

LOWER_LEFT_CORNER = u"\N{BOX DRAWINGS LIGHT UP AND RIGHT}"


class MainWindow(tk.Tk):

    def __init__(self, csv_file: str, imags_dir: str,
                 data_dirs: list[str],
                 column_widths: dict = None):
        super().__init__()

        # styles
        configure_styles(self)

        self.title("MPS Faults")
        self.csv_file = csv_file

        self.data = self.load_csv()
        self.images_dirpath = Path(imags_dir)
        self.data_dirs: list[Path] = [Path(d) for d in data_dirs]
        self.column_widths = {} if column_widths is None else column_widths

        # | ----- | ------- |
        # | Table | preview |
        # | ----- | ------- |
        #
        self.create_table_panel()
        self.create_preview_panel()

    def load_csv(self):
        data = []
        with open(self.csv_file, mode="r", newline="", encoding="utf-8") as fp:
            reader = csv.reader(fp, delimiter=";")
            for row in reader:
                data.append(row)
        return data

    def create_table_panel(self):
        """ Create the table for MPS faults data
        """
        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.table_frame = table_frame

        tree = ttk.Treeview(table_frame,
                            columns=self.data[0],
                            show="headings", selectmode="browse")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tree = tree

        # column headers
        for i, header in enumerate(self.data[0]):
            tree.heading(i, text=header)
            col_w = self.column_widths.get(header, None)
            if col_w is not None:
                logger.warning(f"Set {header} width to {col_w}")
                tree.column(header, width=col_w)

        # tag-wised style
        tree.tag_configure("mtca06", foreground="black")
        tree.tag_configure("non-mtca06", foreground="gray")

        # table data
        for i, row in enumerate(self.data[1:]):
            if row[-1] == "MTCA06":
                _tag = "mtac06"
            else:
                _tag = "non-mtca06"
            tree.insert("", tk.END, iid=i, values=row, tags=(_tag, ))

        tree.bind("<<TreeviewSelect>>", self.on_select_row)

        #
        bottom_frame = ttk.Frame(table_frame)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)

        last_valid_sel_lbl = ttk.Label(bottom_frame)
        last_valid_sel_lbl.pack(side=tk.LEFT, padx=10)
        self.last_valid_sel_lbl = last_valid_sel_lbl

        open_btn = ttk.Button(bottom_frame, text="Open Opt", command=partial(self.on_open, True))
        open_btn.pack(side=tk.RIGHT, padx=10)
        open1_btn = ttk.Button(bottom_frame, text="Open Raw", command=partial(self.on_open, False))
        open1_btn.pack(side=tk.RIGHT, padx=10)

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
        _row = self.tree.selection()
        if _row:
            items = self.tree.item(_row, "values")
            # show the figure if available
            self.display_figure(items)
            logger.debug(f"Selected {_row}: {items}, {self.data[int(_row[0]) + 1]}")

    def on_open(self, is_opt: bool):
        # find the data files
        if self.preview_img_ftid is None:
            return

        data_path = self.find_data_path(self.preview_img_ftid, is_opt)
        if data_path is not None:
            # call plot tool
            cmdline = f"dm-wave plot -opt -i {data_path}" if is_opt else \
                      f"dm-wave plot -i {data_path}"
            subprocess.Popen(cmdline, shell=True)

    def find_data_path(self, ftid: int, is_opt: bool = True) -> Path:
        glob_pattern = f"{ftid}_opt.h5" if is_opt else f"*{ftid}.h5"
        for d in self.data_dirs:
            for pth in d.rglob(glob_pattern):
                if pth.is_file():
                    return pth
        return None

    def update_preview(self):
        self.image_lbl.config(image=self.preview_image)
        self.image_lbl.config(text=self.preview_img_filepath)

    def display_figure(self, row):
        ftid: str = row[0]
        img_filename = f"{ftid}_opt.png"
        img_filepath = self.images_dirpath.joinpath(img_filename)
        if img_filepath.is_file():
            self.preview_image = PhotoImage(file=img_filepath)
            self.preview_img_filepath = img_filepath
            self.preview_img_ftid = int(ftid)
            self.update_preview()
            self.last_valid_sel_lbl.config(text=f"Last previewed event: {self.preview_img_ftid}")
        else:
            pass


def main(mps_faults_path: str, images_dir: str, data_dirs: list[str], **kws):
    app = MainWindow(mps_faults_path, images_dir, data_dirs,
                     column_widths=kws)
    app.minsize(width=1200, height=900)
    app.mainloop()


if __name__ == "__main__":
    csv_file = "./MPS-faults.csv"
    images_dir = "/home/tong/tools/wfdata/final/images"

    column_widths={
        'Fault_ID': 100, 'Time': 200, 'Power': 100,
        'Destination': 150,
        'Ion': 80, 'Type': 100,
        'Description': 200
    }
    main(csv_file, images_dir, **column_widths)
