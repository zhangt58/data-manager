#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import shutil
import subprocess
import sys
import platform
import tkinter as tk
from tkinter import (
    ttk,
    filedialog,
    messagebox,
    scrolledtext,
)
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
RED_COLOR_HEX = "#E74C3C"

# data path cache: {id-o: path, id-r: path, ...}
DATA_PATH_CACHE = {}
# is running on Windows?
_IS_WIN_PLATFORM = platform.system() == "Windows"


class MainWindow(tk.Tk):

    def __init__(self, csv_file: str, trip_info_file: str, imags_dir: str,
                 data_dirs: list[str], fig_dpi: Union[int, None] = None,
                 theme_name: str = "arc", icon_path: Union[str, None] = None,
                 column_widths: dict = None):
        super().__init__()

        # styles
        configure_styles(self, theme_name=theme_name)

        if icon_path is not None:
            self.iconbitmap(icon_path)
        else:
            if _IS_WIN_PLATFORM:
                self.iconbitmap(sys.executable)

        self.lbl_sty_fg = self.style.lookup("TLabel", "foreground")

        #  window title
        self.title("Post-mortem Data Viewer on MPS Faults")

        # create menus
        self.create_menu()

        # screen resolution
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()

        # read the data for the table
        self.csv_file = csv_file
        self.trip_info_file = trip_info_file
        self.data, self.data_info = self.read_data()
        #
        self.images_dirpath = Path(imags_dir)
        self.data_dirs: list[Path] = [Path(d) for d in data_dirs]
        self.column_widths = {} if column_widths is None else column_widths
        self.fig_dpi= fig_dpi

        # info for faults table panel
        self.info_var = tk.StringVar()
        self.info_var.set(DEFAULT_INFO_STRING)
        self.preview_info_var = tk.StringVar()
        self.preview_info_var.set("")
        self.nrecords_var = tk.StringVar()
        self.nrecords_var.set(f"Total {0:>4d}")
        # info for image panel
        self.img_info_var = tk.StringVar()
        self.img_info_var.set("")

        # | --L-- | ---R--- |
        # | Table | preview |
        # | ----- | ------- |
        #
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=4, minsize=500)
        main_frame.rowconfigure(0, weight=1)
        self.main_frame = main_frame
        #
        left_panel = ttk.Frame(self.main_frame, padding=2, borderwidth=1)
        left_panel.grid(row=0, column=0, sticky="nsew")
        self.left_panel = left_panel
        #
        self.right_panel = ttk.Frame(self.main_frame, padding=2, borderwidth=2)
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        #
        self.create_table_panel()
        self.create_preview_panel()

    def on_check_updates(self):
        """ Check if new versions are available, Windows only.
        """
        import re
        logger.info("Checking if new versions are avaiable...")
        pkg_dir = Path("I:/analysis/linac-data/wfdata/tools")
        pkg_name_pattern = "DataManager-Wave*.exe"
        latest_pkg_path = sorted(pkg_dir.glob(pkg_name_pattern))[-1]
        v = re.search(r"_(\d+\.\d+(?:\.\d+)?(?:-\d+)?)\.", str(latest_pkg_path))
        if v is not None:
            latest_pkg_ver = v.group(1)
            if latest_pkg_ver > _version:
                logger.info(f"New version {latest_pkg_ver} is available!")
                r = messagebox.askquestion(title="Checking for Updates",
                        message=f"DataManager-Wave {latest_pkg_ver} is available!",
                        detail=f"Press YES to upgrade from {_version}."
                    )
                if r == messagebox.YES:
                    subprocess.call(f"{latest_pkg_path} /i", shell=True)
                return
        messagebox.showinfo(title="Checking for Updates",
            message="No Updates Available.",
        )

    def create_menu(self):
        """ Create the menu bar and the items.
        """
        def on_help():
            import webbrowser
            webbrowser.open("https://wikihost.frib.msu.edu/AcceleratorPhysics/doku.php?id=data:linacdata")

        def on_exit():
            r = messagebox.askquestion(title="Exit DM-Wave",
                    message=f"Are you sure to close DM-Wave?",
                )
            if r == messagebox.YES:
                self.destroy()

        def on_apply_theme(theme_name: str):
            logger.debug(f"Applying theme: {theme_name}")
            configure_styles(self, theme_name=theme_name)

        #
        menu_bar = tk.Menu(self)
        # File
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", accelerator="Ctrl+Q", command=on_exit)
        # View
        view_menu = tk.Menu(menu_bar, tearoff=0)
        theme_subm = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_subm)
        # View -> Theme
        for _theme in ("adapta", "arc", "breeze", "scidblue", "vista"):
            theme_subm.add_command(label=_theme, command=partial(on_apply_theme, _theme))
        # Help
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Documentation", accelerator="F1", command=on_help)
        if _IS_WIN_PLATFORM:
            help_menu.add_command(label="Check for Updates", command=self.on_check_updates)
        help_menu.add_command(label="About", accelerator="Ctrl+A",
                              command=lambda:self.on_about(self))
        #
        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="View", menu=view_menu)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        #
        self.config(menu=menu_bar)
        self.bind("<Control-q>", lambda e:on_exit())
        self.bind("<Control-a>", lambda e:self.on_about(self))
        self.bind("<F1>",lambda e:on_help())

    def read_data(self, filter: Union[str, None] = None) -> tuple[pd.DataFrame, Union[pd.DataFrame, None]]:
        """ Read a list or rows data from *csv_file*.
        # filter the "Description" column: MTCA06
        # filter the "T Window" column: 150us
        """
        # main event table
        df = pd.read_csv(self.csv_file, delimiter=";")
        # trip info table
        if self.trip_info_file is not None:
            df_info = pd.read_hdf(self.trip_info_file)[
                        ["ID", "devices", "t window", "threshold"]
                    ].rename(columns={
                        "ID": "Fault_ID",
                        "devices": "Devices",
                        "t window": "T Window",
                        "threshold": "Threshold"
                    })
        else:
            df_info = None
        # filter main
        if filter == "MTCA06":
            df = df[df["Description"]=="MTCA06"].reset_index(drop=True)
        # filter info
        if filter == "150us":
            if df_info is None:
                self.info_var.set("MTCA trip info is not available!")
            else:
                _df = df_info.set_index('Fault_ID')
                idx = _df[_df["T Window"].astype(str).str.contains(
                    "Diff 150[^0]s", regex=True)].index
                df1 = df.set_index('Fault_ID')
                idx1 = df1.index[df1.index.isin(idx)]
                df = df1.loc[idx1].reset_index()
                self.info_var.set(DEFAULT_INFO_STRING)
        return df, df_info

    def create_table_panel(self):
        """ Create the table for MPS faults data
        """
        #
        # | main tree frame
        # | trip-info tree frame
        # | bottom frame
        #
        data_frame = ttk.Frame(self.left_panel)
        data_frame.pack(fill=tk.BOTH, expand=True)
        #
        data_frame.rowconfigure(0, weight=1)
        data_frame.rowconfigure(1, weight=0)
        data_frame.rowconfigure(2, weight=0)
        data_frame.columnconfigure(0, weight=1)
        # data_frame.grid_propagate(False)

        tree_frame = ttk.Frame(data_frame)
        tree_frame.grid(row=0, column=0, sticky="nsew")
        # place tree
        self.tree = self.place_table(tree_frame, self.data.columns.to_list(),
                                     xscroll_on=True, yscroll_on=True,
                                     column_widths=self.column_widths)

        self.tree.bind("<<TreeviewSelect>>", self.on_select_row)

        # trip info tree
        info_tree_frame = ttk.Frame(data_frame)
        info_tree_frame.grid(row=1, column=0, sticky="nsew")
        #
        self.info_tree = self.place_table(info_tree_frame, self.data_info.columns.to_list(),
                                          xscroll_on=True, yscroll_on=True,
                                          column_widths=self.column_widths)
        # tag-wised style
        self.info_tree.tag_configure("n/a", foreground="gray")
        self.info_tree.tag_configure("valid", foreground=RED_COLOR_HEX)

        # main table data
        self.present_main_data()

        # The widgets below the tree_frame
        # frame1
        # |- [All] [MTCA06] Event on Preview
        # frame2
        # |- Info: xxxx
        ctrl_frame = ttk.Frame(data_frame)
        ctrl_frame.grid(row=2, column=0, sticky="nsew")

        ctrl_frame1 = ttk.Frame(ctrl_frame)
        ctrl_frame1.pack(side=tk.TOP, fill=tk.X, expand=True, padx=5, pady=5)
        ctrl_frame2 = ttk.Frame(ctrl_frame)
        ctrl_frame2.pack(side=tk.BOTTOM, fill=tk.X, expand=True, padx=5, pady=2)
        # all
        reload_all_btn = ttk.Button(ctrl_frame1, text="Reload All",
                                    command=partial(self.on_reload, None))
        reload_all_btn.pack(side=tk.LEFT, padx=2)
        # description = MTCA06
        reload_mtca_btn = ttk.Button(ctrl_frame1, text="MTCA06",
                                     command=partial(self.on_reload, "MTCA06"))
        reload_mtca_btn.pack(side=tk.LEFT, padx=10)
        # T Window has 150us (need --trip-info-file)
        reload_fast_trip_btn = ttk.Button(ctrl_frame1, text=f"Diff 150{MU_GREEK}s",
                                          command=partial(self.on_reload, f"150us"))
        reload_fast_trip_btn.pack(side=tk.LEFT, padx=10)
        #
        # total entries
        nrows_lbl = ttk.Label(ctrl_frame1, textvariable=self.nrecords_var)
        nrows_lbl.pack(side=tk.RIGHT, padx=5)
        #
        preview_info_lbl = ttk.Label(ctrl_frame1, textvariable=self.preview_info_var)
        preview_info_lbl.pack(side=tk.RIGHT, padx=10)
        self.preview_info_lbl = preview_info_lbl

        # info label
        info_lbl = ttk.Label(ctrl_frame2, textvariable=self.info_var)
        info_lbl.pack(side=tk.LEFT, fill=tk.X, padx=2)
        self.info_lbl = info_lbl

    def on_about(self, parent):
        about_dialog = tk.Toplevel(parent)
        about_dialog.title("About DM-Wave")
        #
        frame = ttk.Frame(about_dialog)
        frame.pack(expand=True, fill=tk.BOTH)
        #
        text_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD,
                                              width=50, height=15)
        text_area.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Insert your about information into the text area
        about_text = f"""Data Manager - Wave
Version {_version}

This app is developed to manage the post-mortem BCM/BPM waveform data on MPS trip events, and
provide the tools for post-processing and data visualization.

This is the GUI app for browsing the data in images along with the MPS trip event information.

Copyright (c) 2025 Tong Zhang, FRIB, Michigan State University."""
        text_area.insert(tk.END, about_text)
        text_area.config(state=tk.DISABLED)  # Make it read-only

        close_button = ttk.Button(frame, text="Close", command=about_dialog.destroy)
        close_button.pack(pady=5)


        # position on top of the middle of the main
        w0, h0 = 600, 400
        main_w, main_h = parent.winfo_width(), parent.winfo_height()
        main_x, main_y = parent.winfo_x(), parent.winfo_y()
        x = main_x + (main_w - w0) // 2
        y = main_y + (main_h - h0) // 2
        about_dialog.geometry(f"{w0}x{h0}+{x}+{y}")

        about_dialog.transient(parent)  # Make it a dialog window
        about_dialog.grab_set()  # Ensure user interaction only with the dialog
        #
        parent.wait_window(about_dialog)  # Wait until the dialog is closed

    def create_preview_panel(self):
        # right panel
        # |- image label
        # |- [fit]   [Plot Raw]  [Plot Opt]
        # |-         [Get Raw ]  [Get Opt ]

        self.right_panel.rowconfigure(0, weight=1)
        self.right_panel.rowconfigure(1, weight=0)
        self.right_panel.columnconfigure(0, weight=1)
        # image
        img_frame = ttk.Frame(self.right_panel)
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
        ctrl_frame = ttk.Frame(self.right_panel)
        ctrl_frame.grid(row=1, column=0, sticky="ew", pady=5)
        #
        ctrl_frame1 = ttk.Frame(ctrl_frame)
        ctrl_frame1.pack(side=tk.TOP, fill=tk.X, expand=True, padx=5, pady=5)
        ctrl_frame2 = ttk.Frame(ctrl_frame)
        ctrl_frame2.pack(side=tk.BOTTOM, fill=tk.X, expand=True, padx=5, pady=2)
        #
        # fit image size
        fit_btn = ttk.Button(ctrl_frame1, text="Fit", command=self.on_fit_image,
                             width=4)
        fit_btn.pack(side=tk.LEFT, padx=5)
        # plot
        open_btn = ttk.Button(ctrl_frame1, text="Plot Opt", command=partial(self.on_open, True))
        open_btn.pack(side=tk.RIGHT, padx=5)
        open1_btn = ttk.Button(ctrl_frame1, text="Plot Raw", command=partial(self.on_open, False))
        open1_btn.pack(side=tk.RIGHT, padx=10)

        # data/image info
        img_info_lbl = ttk.Label(ctrl_frame2, textvariable=self.img_info_var)
        img_info_lbl.pack(side=tk.LEFT, fill=tk.X, padx=5)
        self.img_info_lbl = img_info_lbl

        # get data
        opt_data_btn = ttk.Button(ctrl_frame2, text="Get Opt", command=partial(self.on_get_data, True))
        opt_data_btn.pack(side=tk.RIGHT, padx=5)
        raw_data_btn = ttk.Button(ctrl_frame2, text="Get Raw", command=partial(self.on_get_data, False))
        raw_data_btn.pack(side=tk.RIGHT, padx=10)

    def on_get_data(self, is_opt: bool):
        """ Get the data, opt or raw
        """
        data_path = self.find_data_path(self.loaded_image_ftid, is_opt)
        if data_path is None or not data_path.is_file():
            self.img_info_var.set(f"Invalid data path for ID {self.loaded_image_ftid}.")
            self.img_info_lbl.config(foreground=RED_COLOR_HEX)
        else:
            self.img_info_lbl.config(foreground=self.lbl_sty_fg)
            dst_pth, err = save_data(data_path)
            if dst_pth is None:
                return
            if err is None:
                self.img_info_var.set(f"Downloaded {data_path.name}")
                self.img_info_lbl.config(foreground=self.lbl_sty_fg)
                r = messagebox.showinfo(
                      title="Download Data",
                      message=f"Successfully Downloaded {data_path.name}",
                      detail=f"Saved as {dst_pth}",
                      type=messagebox.OKCANCEL)
                if r == messagebox.OK:
                    if _IS_WIN_PLATFORM:
                        _cmd = f"explorer /select,{dst_pth}"
                        logger.info(f"Revealing {dst_pth} in File Explorer")
                        subprocess.Popen(_cmd, shell=True)
            else:
                messagebox.showwarning(
                    title="Download Data",
                    message=f"Error Downloading {data_path.name}",
                    detail=err
                )

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
            logger.debug(f"Selected {_row}: {items}, {self.data.iloc[int(_row)].to_list()}")
            # show the trip info
            self.display_info(items)

    def on_reload(self, filter: Union[str, None] = None):
        """ Reload the MPS faults table.
        """
        self.refresh_table_data(filter)
        # clear the cache
        DATA_PATH_CACHE.clear()

    def on_open(self, is_opt: bool):
        # find the data files
        data_path = self.find_data_path(self.loaded_image_ftid, is_opt)
        if data_path is None or not data_path.is_file():
            _s = "opt" if is_opt else "raw"
            msg = f"Invalid {_s} data file for ID {self.loaded_image_ftid}"
            self.img_info_var.set(msg)
            self.img_info_lbl.config(foreground=RED_COLOR_HEX)
            logger.error(msg)
            # remove from the cache
            DATA_PATH_CACHE.pop(f"{self.loaded_image_ftid}-r", None)
            DATA_PATH_CACHE.pop(f"{self.loaded_image_ftid}-o", None)
        else:
            # call plot tool
            cmdline = f"dm-wave plot -opt -i {data_path}" if is_opt else \
                      f"dm-wave plot -i {data_path}"
            if self.fig_dpi is not None:
                cmdline += f" --fig-dpi {self.fig_dpi}"
            _info_msg = f"Ploting with the {data_path} (raw)" if not is_opt else \
                        f"Ploting with the {data_path} (opt)"
            logger.info(_info_msg)
            subprocess.Popen(cmdline, shell=True)
            self.img_info_var.set(f"Plotting with {data_path.name}")
            self.img_info_lbl.config(foreground=self.lbl_sty_fg)

    def find_data_path(self, ftid: int, is_opt: bool = True) -> Union[Path, None]:
        if ftid is None:
            return None
        k = f"{ftid}-o" if is_opt else f"{ftid}-r"
        if k in DATA_PATH_CACHE:
            logger.debug(f"Found data file at {DATA_PATH_CACHE.get(k)} (cached)")
            return DATA_PATH_CACHE.get(k)
        glob_pattern = f"*{ftid}_opt.h5" if is_opt else f"*{ftid}.h5"
        for d in self.data_dirs:
            for pth in d.rglob(glob_pattern):
                if pth.is_file():
                    DATA_PATH_CACHE[k] = pth
                    logger.debug(f"Found data file at {DATA_PATH_CACHE.get(k)}")
                    return pth
        logger.debug(f"No data file found for ID {ftid}")
        return None

    def find_image_path(self, ftid: int) -> Union[Path, None]:
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
        ftid: int = int(row[0])
        img_filepath = self.find_image_path(ftid)
        if img_filepath is not None:
            self.loaded_image_ftid = ftid
            self.loaded_image_var.set(str(img_filepath))
            self.preview_info_var.set(f"Event on Preview: {ftid}")
            self.info_var.set(DEFAULT_INFO_STRING)
            self.info_lbl.config(foreground=self.lbl_sty_fg)
        else:
            msg = f"No image found for ID {ftid}"
            logger.warning(msg)
            self.info_var.set(msg)
            self.info_lbl.config(foreground=RED_COLOR_HEX)

    def place_table(self, parent_frame, headers: list[str],
                    xscroll_on: bool = True, yscroll_on: bool = True,
                    column_widths: dict[str, int] = {}):
        tree = ttk.Treeview(parent_frame,
                            columns=headers,
                            show="headings", selectmode="browse")
        # scrollbars
        if xscroll_on:
            x_scroll = ttk.Scrollbar(parent_frame, orient=tk.HORIZONTAL, command=tree.xview)
            x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
            tree.configure(xscrollcommand=x_scroll.set)
        if yscroll_on:
            y_scroll = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL, command=tree.yview)
            y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            tree.configure(yscrollcommand=y_scroll.set)
        #
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # set column headers
        self._set_table_headers(tree, headers, column_widths)
        return tree

    def _set_table_headers(self, tree, headers: list[str], column_widths: dict[str, int]):
        anchor_map = {
            "Fault_ID": tk.CENTER,
            "Power": tk.E,
            "Destination": tk.CENTER,
            "Devices": tk.CENTER,
        }
        anchor_default = tk.W
        for i, header in enumerate(headers):
            tree.heading(i, text=header)
            col_w =column_widths.get(header, None)
            if col_w is not None:
                logger.debug(f"Set {header} width to {col_w}")
                tree.column(header, width=col_w,
                            anchor=anchor_map.get(header, anchor_default))

    def present_main_data(self):
        """ Present the data to the main table.
        """
        for i, row in self.data.iterrows():
            row.Power = f"{row.Power/1e3:.2f} kW" if row.Power > 1e3 else f"{int(row.Power)} W"
            self.tree.insert("", tk.END, iid=i, values=row.to_list())

        # post the total number of entries
        self.nrecords_var.set(f"Total {self.data.shape[0]:>4d}")

    def display_info(self, row):
        ftid: int = int(row[0])
        hit_row = self.data_info[self.data_info["Fault_ID"]==ftid]
        # expand to rows
        hit_df = hit_row.explode(column=self.data_info.columns[-3:].to_list()).reset_index(drop=True)
        self.info_tree.delete(*self.info_tree.get_children())
        for i, row in hit_df.iterrows():
            if row["Devices"] == "N/A":
                _tag = "n/a"
            else:
                _tag = "valid"
            self.info_tree.insert("", tk.END, iid=i, values=row.to_list(), tags=(_tag, ))

    def refresh_table_data(self, filter: Union[str, None] = None):
        """ Re-read the data and refresh the table.
        """
        self.data, self.data_info = self.read_data(filter)
        self.tree.delete(*self.tree.get_children())
        self.present_main_data()


def save_data(src_file_path: Path) -> tuple[Union[Path, None], Union[str, None]]:
    initial_dir = Path("~").expanduser().joinpath("Downloads")
    dst_file_path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".h5",
            filetypes=[("HDF5 Files", "*.h5"), ("All Files", "*.*")],
            initialdir=initial_dir,
            initialfile=src_file_path.name,
    )
    if not dst_file_path:
        return None, None
    dst_file_path = Path(dst_file_path)
    try:
        shutil.copy2(src_file_path, dst_file_path)
    except Exception as e:
        logger.error(f"Copy failed {src_file_path} -> {dst_file_path}")
        return dst_file_path, f"{e}"
    else:
        logger.debug(f"Copied {src_file_path} -> {dst_file_path}")
        return dst_file_path, None


def main(mps_faults_path: str, trip_info_file: str, images_dir: str, data_dirs: list[str],
         geometry: str = "1600x1200", fig_dpi: Union[int, None] = None, theme_name: str = "arc",
         icon_path: Union[str, None] = None, **kws):
    app = MainWindow(mps_faults_path, trip_info_file, images_dir, data_dirs, fig_dpi,
                     theme_name, icon_path, column_widths=kws)
    app.geometry(geometry)
    w, h = geometry.split("x")
    app.minsize(width=int(w), height=int(h))
    logger.info(f"Set the initial size {geometry}")
    app.mainloop()

