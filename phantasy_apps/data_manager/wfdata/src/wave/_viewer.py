#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
from pathlib import Path
from _tk import configure_styles

UNCHKED = u'\N{BALLOT BOX}'
CHECKED = u'\N{BALLOT BOX WITH CHECK}'


class MainWindow(tk.Tk):

    def __init__(self, csv_file: str, imags_dir: str,
                 column_widths: dict = None):
        super().__init__()

        # scaling
        print(self.tk.call('tk', 'scaling'))
        self.tk.call('tk', 'scaling', 1.0)
        print(self.tk.call('tk', 'scaling'))

        # styles
        configure_styles(self)

        self.title("MPS Faults")
        self.csv_file = csv_file
        self.selected_rows = set()

        self.data = self.load_csv()
        self.images_dirpath = Path(imags_dir)
        self.column_widths = {} if column_widths is None else column_widths

        # | ----- | ------- |
        # | Table | preview |
        # | ----- | ------- |
        #
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
                            columns=("Select", *(self.data[0])),
                            show="headings")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tree = tree

        # column headers
        tree.heading("Select", text="")
        tree.column("Select", width=50)
        for i, header in enumerate(self.data[0]):
            tree.heading(i + 1, text=header)
            col_w = self.column_widths.get(header, None)
            if col_w is not None:
                print(f"Set {header} width to {col_w}")
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
            tree.insert("", tk.END, iid=i, values=("", *row), tags=(_tag, ))
            tree.set(i, "Select", UNCHKED)

        tree.bind("<Button-1>", self.on_check_row)
        tree.bind("<<TreeviewSelect>>", self.on_select_row)

        #
        bottom_frame = ttk.Frame(table_frame)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)

        unchk_all_btn = ttk.Button(bottom_frame, text=f"{UNCHKED} ALL", command=self.on_unchk_all)
        unchk_all_btn.pack(side=tk.LEFT, padx=5)

        chk_all_btn = ttk.Button(bottom_frame, text=f"{CHECKED} ALL", command=self.on_chk_all)
        chk_all_btn.pack(side=tk.LEFT, padx=10)

        sts_lbl = ttk.Label(bottom_frame, text="Selected Rows: 0")
        sts_lbl.pack(side=tk.LEFT, padx=10)
        self.sts_lbl = sts_lbl

        open_btn = ttk.Button(bottom_frame, text="Open", command=self.on_open)
        open_btn.pack(side=tk.RIGHT, padx=10)

    def create_preview_panel(self):
        self.preview_frame = ttk.Frame(self)
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10, pady=10)

        self.image_lbl = ttk.Label(self.preview_frame)
        self.image_lbl.pack(fill=tk.BOTH, expand=True)
        self.preview_image = None
        self.update_preview()

    def on_unchk_all(self):
        """ Mark all unchecked.
        """
        self.selected_rows.clear()
        for row in self.tree.get_children():
            self.tree.set(row, "Select", UNCHKED)
        self._update_checked_sts()

    def on_chk_all(self):
        """ Make all checked.
        """
        for row in self.tree.get_children():
            self.selected_rows.add(row)
            self.tree.set(row, "Select", CHECKED)
        self._update_checked_sts()

    def on_check_row(self, evt):
        region = self.tree.identify_region(evt.x, evt.y)
        if region == "cell":
            column = self.tree.identify_column(evt.x)
            row = self.tree.identify_row(evt.y)
            if column == "#1":
                if row in self.selected_rows:
                    self.selected_rows.remove(row)
                    self.tree.set(row, "Select", UNCHKED)
                else:
                    self.selected_rows.add(row)
                    self.tree.set(row, "Select", CHECKED)
                self._update_checked_sts()

    def on_select_row(self, evt):
        _row = self.tree.selection()
        if _row:
            items = self.tree.item(_row, "values")
            # show the figure if available
            self.display_figure(items)

    def on_open(self):
        if not self.selected_rows:
            messagebox.showinfo("Info", "No rows selected!")
            return
        print(self.selected_rows)

    def update_preview(self):
        if self.preview_image is not None:
            self.image_lbl.config(image=self.preview_image)
        else:
            pass
            # self.image_lbl.config(text="Error: Image is not available!")

    def display_figure(self, row):
        ftid: str = row[1]
        img_filename = f"{ftid}_opt.png"
        img_filepath = self.images_dirpath.joinpath(img_filename)
        if img_filepath.is_file():
            # print(f"Show {img_filepath}")
            self.preview_image = PhotoImage(file=img_filepath)
            self.update_preview()
        else:
            pass

    def _update_checked_sts(self):
        self.sts_lbl.config(text=f"Selected Rows: {len(self.selected_rows)}")


if __name__ == "__main__":
    csv_file = "./MPS-faults.csv"
    images_dir = "/home/tong/tools/wfdata/final/images"

    app = MainWindow(csv_file, images_dir,
                     column_widths={
                         'Fault_ID': 100, 'Time': 200, 'Power': 100,
                         'Destination': 150,
                         'Ion': 80, 'Type': 100,
                         'Description': 200
                     })
    app.minsize(width=1200, height=900)
    app.mainloop()
