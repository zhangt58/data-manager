#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import tkinter as tk
from functools import (
    partial,
    reduce
)
from itertools import cycle
from tkinter import (
    ttk,
    messagebox
)
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)
from matplotlib.text import Text
from PIL import Image, ImageTk

from ._data import (
    BCM_FSCALE_NAME_MAP,
    BCM_TRACE_VIS_MAP,
    BPM_TRACE_VIS_MAP,
)
from ._log import logger
from .resources import (
    rc_bcm_image_bytes,
    rc_bpm_image_bytes
)

# matplotlib.pyplot.rcParams['axes.prop_cycle']
_LINE_COLORS = [
    '#1f77b4',
    '#ff7f0e',
    '#2ca02c',
    '#d62728',
    '#9467bd',
    '#8c564b',
    '#e377c2',
    '#7f7f7f',
    '#bcbd22',
    '#17becf'
]

MU_GREEK = u"\N{GREEK SMALL LETTER MU}"


class FigureWindow(tk.Toplevel):
    # Present figures in a Tkinter GUI,
    # keywords: fig_dpi, theme_name, dbcm_dfs: list[pd.DataFrame], bcm_fscale_maps: list[dict]
    def __init__(self, figures: list[tuple],
                 window_title: str, grid: tuple[int, int],
                 padx: int = 5, pady: int = 5, notes: str = "",
                 **kws):
        super().__init__(kws.get('parent', None))

        # styles
        configure_styles(self, theme_name=kws.get("theme_name", "arc"))
        #
        self.title(window_title)
        self.protocol("WM_DELETE_WINDOW", self.quit)

        # Create a frame for the figures
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        nrows, ncols = grid
        for i in range(nrows):
            main_frame.rowconfigure(i, weight=1)
        for j in range(ncols):
            main_frame.columnconfigure(j, weight=1)

        dbcm_dfs = kws.get('dbcm_dfs', None)
        bcm_fscale_maps = kws.get('bcm_fscale_maps', None)

        # layout figures
        for i, (fig, fig_title) in enumerate(figures):
            irow, icol = i // ncols, i % ncols
            dbcm_df = dbcm_dfs[i] if dbcm_dfs is not None else None
            bcm_fscale_map = bcm_fscale_maps[i] if bcm_fscale_maps is not None else None
            self.place_figure(main_frame, fig, fig_title, irow, icol, padx, pady,
                              fig_dpi=kws.get('fig_dpi', None), dbcm_df=dbcm_df,
                              bcm_fscale_map=bcm_fscale_map)

        # bottom area (notes and Quit button)
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # notes area
        notes_text = tk.Text(bottom_frame, height=3)
        notes_text.insert("1.0", notes)
        notes_text.config(state="disabled")
        notes_text.pack(side=tk.LEFT, fill=tk.X, padx=padx, pady=pady, expand=True)

        # quit button
        quit_btn = ttk.Button(bottom_frame, text="Quit", command=self.quit)
        quit_btn.pack(side=tk.RIGHT, fill=tk.X, pady=pady, padx=padx)

    def place_figure(self, parent, figure, title: str, row: int, col: int,
                     padx: int = 5, pady: int = 5, fig_dpi: int = None, **kws):
        # keywords: dbcm_df: pd.DataFrame, bcm_fscale_map: dict
        dbcm_df = kws.get('dbcm_df', None)
        bcm_fscale_map = kws.get('bcm_fscale_map', None)
        #
        frame = ttk.LabelFrame(parent, text=title, borderwidth=1, relief=tk.GROOVE)
        frame.grid(row=row, column=col, padx=padx, pady=pady, sticky="nsew")

        # tools frame:
        #      0         1          2
        #0 |toolbar | bcm_ctrl | X-Axis |
        #1 |phase   |AVG-chk(*)| Y-Axis |
        # figure frame
        # misc frame
        # BCM trace visibility ctrl frame
        # BPM trace visibility ctrl frame
        # (*) AVG-chk: a row of Checkbuttons for applying rolling average at
        #              different window size
        #
        tools_frame = ttk.Frame(frame)
        tools_frame.pack(fill=tk.X, padx=2, pady=2)
        tools_frame.columnconfigure(0, weight=2)
        tools_frame.columnconfigure(1, weight=1)
        tools_frame.columnconfigure(2, weight=0)

        tb_frame = ttk.Frame(tools_frame)
        bcm_ctrl_frame = ttk.Frame(tools_frame)
        xaxis_frame = ttk.Frame(tools_frame)
        tb_frame.grid(row=0, column=0, sticky="ew")
        bcm_ctrl_frame.grid(row=0, column=1, sticky="ew")
        xaxis_frame.grid(row=0, column=2, sticky="ew")
        #
        pha_frame = ttk.Frame(tools_frame)
        wave_roll_frame = ttk.Frame(tools_frame)
        yaxis_frame = ttk.Frame(tools_frame)
        pha_frame.grid(row=1, column=0, sticky="ew")
        wave_roll_frame.grid(row=1, column=1, sticky="ew")
        yaxis_frame.grid(row=1, column=2, sticky="ew")

        # figure
        fig_frame = ttk.Frame(frame)
        fig_frame.pack(fill=tk.BOTH, expand=True)

        # change figure dpi
        if fig_dpi is not None:
            figure.set_dpi(fig_dpi)

        # get initial fontsizes
        self.fs_init: list[float] = [
            # title
            figure.get_axes()[0].title.get_fontsize(),
            # xylabel
            figure.get_axes()[0].xaxis.label.get_fontsize(),
            # xyticklabel
            figure.get_axes()[0].xaxis.get_ticklabels()[0].get_fontsize(),
        ]
        #
        canvas = FigureCanvasTkAgg(figure, master=fig_frame)
        canvas.draw_idle()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        #
        tb = NavigationToolbar2Tk(canvas, tb_frame)
        tb.update()

        # misc_frame (below figure frame)
        # other controls
        misc_frame = ttk.Frame(frame)
        misc_frame.pack(fill=tk.X, padx=2, pady=2)

        # lw
        lw_lbl = ttk.Label(misc_frame, text="Line Width")
        lw_sbox = ttk.Spinbox(misc_frame, from_=0.5, to=5, increment=0.5,
                               state='readonly', width=4, justify=tk.CENTER,
                               command=partial(self.on_update_lw, figure))
        lw_lbl.pack(side=tk.LEFT, padx=2)
        lw_sbox.pack(side=tk.LEFT, padx=2)
        self.lw_sbox = lw_sbox
        # ds
        ds_lbl = ttk.Label(misc_frame, text="Style")
        self.ds_var = tk.StringVar()
        ds_cbb = ttk.Combobox(misc_frame, textvariable=self.ds_var,
                              state="readonly", justify=tk.CENTER,
                              values=["default", "steps"], width=8)
        ds_lbl.pack(side=tk.LEFT, padx=5)
        ds_cbb.pack(side=tk.LEFT, padx=2)
        ds_cbb.set("default")
        ds_cbb.bind("<<ComboboxSelected>>", partial(self.on_ds_changed, figure))
        # font size
        fs_lbl = ttk.Label(misc_frame, text="+FontSize")
        fs_inc_sbox = ttk.Spinbox(misc_frame, from_=-4, to=10, increment=0.5,
                                  state='readonly', width=4, justify=tk.CENTER,
                                  command=partial(self.on_update_fontsize, figure))
        fs_lbl.pack(side=tk.LEFT, padx=5)
        fs_inc_sbox.pack(side=tk.LEFT, padx=2)
        self.fs_inc_sbox = fs_inc_sbox

        # legend on/off checkbox
        self.legend_toggle_var = tk.BooleanVar(value=True)
        legend_toggle_chkbox = ttk.Checkbutton(misc_frame,
                text="Legend", width=6,
                variable=self.legend_toggle_var,
                command=partial(self.on_toggle_legends, figure))
        legend_toggle_chkbox.pack(side=tk.RIGHT, padx=2)

        # visibility controls
        hline = ttk.Separator(frame, orient="horizontal")
        hline.pack(fill=tk.X, padx=2, pady=1)
        self.bcm_vis_ctrl_frame = bcm_vis_ctrl_frame = ttk.Frame(frame)
        bcm_vis_ctrl_frame.pack(fill=tk.X, padx=2, pady=2)
        bpm_vis_ctrl_frame = ttk.Frame(frame)
        bpm_vis_ctrl_frame.pack(fill=tk.X, padx=2, pady=2)

        # phase frame (variables)
        ax_pha = None
        # mag
        ax_mag = None
        # a list of np.ndarray/np.ma.MaskedArray of phase values
        self.pha0: list[Union[np.ndarray, np.ma.MaskedArray]] = []
        # time array of phase figure
        self.pha0_t: np.ndarray = None

        # bcm raw trace
        self.bcm_ydata0: list[np.ndarray] = []
        self.bcm_fscales: list[float] = []
        ax_bcm = None

        # xaxis frame
        i = 1
        sync_lbl = ttk.Label(xaxis_frame, text="Sync ↔")
        sync_lbl.pack(side=tk.LEFT, padx=1)
        for ax in figure.get_axes():
            ylbl = ax.get_ylabel()
            if ylbl == "NPERMIT":
                continue
            ax.text(-0.05, 1.05, f"{i}", transform=ax.transAxes,
                    size=self.fs_init[0],
                    bbox=dict(facecolor='w', alpha=0.9, edgecolor='k'))
            if 'Phi' in ylbl:
                ax_pha = ax
                ax_pha_ylabel0: str = ylbl
                self.pha0 = [l.get_ydata() for l in ax.get_lines()]
                if len(ax.get_lines()) != 0:
                    self.pha0_t = ax.get_lines()[0].get_xdata()
                else:
                    self.pha0_t = None
                # print(type(self.pha0[0]), self.pha0[0][:100])
            elif 'Current' in ylbl:
                ax_bcm = ax
                if bcm_fscale_map is not None:
                    for l in ax.get_lines():
                        name = l.get_label()
                        _fs = bcm_fscale_map[BCM_FSCALE_NAME_MAP[name]]
                        self.bcm_fscales.append(_fs)
                        self.bcm_ydata0.append(l.get_ydata())
            elif 'Magnitude' in ylbl:
                ax_mag = ax

            sync_btn = ttk.Button(xaxis_frame, text=f"{i}", width=3,
                                  command=partial(sync_xlimits, figure, ax))
            sync_btn.pack(side=tk.LEFT, padx=1)
            i += 1

        # bcm_ctrl frame
        bcm_ctrl_lbl = ttk.Label(bcm_ctrl_frame, text="BCM RAW")
        self.bcm_ctrl_lbl = bcm_ctrl_lbl
        self.bcm_norm_toggle_var = tk.BooleanVar(value=False)
        bcm_norm_toggle_chkbox = ttk.Checkbutton(bcm_ctrl_frame,
                text="Normlize", width=9,
                variable=self.bcm_norm_toggle_var,
                command=partial(self.on_normalize_bcm_traces, bcm_fscale_map,
                                figure, ax_bcm)
        )
        self.bcm_norm_toggle_chkbox = bcm_norm_toggle_chkbox
        #
        self.show_as_dbcm_toggle_var = tk.BooleanVar(value=False)
        show_as_dbcm_chkbox = ttk.Checkbutton(bcm_ctrl_frame,
                text="DBCM", width=5,
                variable=self.show_as_dbcm_toggle_var,
                command=partial(self.on_plot_diff_bcm_traces,
                                figure, ax_bcm)
        )
        self.show_as_dbcm_chkbox = show_as_dbcm_chkbox
        # button for hints
        bcm_help_btn = ttk.Button(bcm_ctrl_frame, text="?", width=2,
                                  command=partial(self.on_help_bcm_controls, bcm_fscale_map))
        if dbcm_df is None or dbcm_df.empty:
            show_as_dbcm_chkbox.config(state="disabled")
        else:
            self.dbcm_df = dbcm_df
            self.dbcm_plots = None
        if bcm_fscale_map is None or not bcm_fscale_map:
            bcm_norm_toggle_chkbox.config(state="disabled")
            bcm_help_btn.config(state="disabled")
        #
        bcm_ctrl_lbl.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        bcm_help_btn.pack(side=tk.RIGHT, padx=2)
        bcm_norm_toggle_chkbox.pack(side=tk.RIGHT, padx=2)
        show_as_dbcm_chkbox.pack(side=tk.RIGHT, padx=2)

        # curve visibility controls
        self._layout_win_map: dict = {'BCM': None, 'BPM': None}
        self._layout_imgtk_map: dict = {'BCM': None, 'BPM': None}
        self._curve_vis_map: dict[str, tk.BooleanVar] = {}
        self._create_bcm_vis_btns(bcm_vis_ctrl_frame, figure, ax_bcm)
        self._create_bpm_vis_btns(bpm_vis_ctrl_frame, figure, ax_pha, ax_mag)

        # wave_roll_frame: rolling average
        # keys: window size (str), '15', '150', etc.
        self.roll_var_map: dict = {}
        self.roll_chkbox_map: dict = {}
        # keys: line labels (original) + line label + win_size_s (rolling averaged ones)
        self.trace_data_map: dict = {}
        #
        for win_size in (15, 150):
            win_size_s = str(win_size)
            _v = self.roll_var_map.setdefault(win_size_s, tk.BooleanVar(value=False))
            _o = ttk.Checkbutton(wave_roll_frame,
                                 text=f"{win_size}{MU_GREEK}s",
                                 variable=_v,
                                 command=partial(
                                     self.on_rolling_wave, win_size,
                                     figure, ax_bcm, ax_pha, ax_mag
                                 )
                 )
            _o.pack(side=tk.LEFT, padx=2)
            self.roll_chkbox_map[win_size_s] = _o


        # yaxis_frame
        # add a button to adjust auto scale Y limits
        auto_y_lbl = ttk.Label(yaxis_frame, text="Auto Y")
        auto_y_btn = ttk.Button(yaxis_frame, text="↕", width=2,
                                command=partial(on_auto_y, figure))
        auto_y_lbl.pack(side=tk.LEFT, padx=1)
        auto_y_btn.pack(side=tk.RIGHT, padx=1)

        # pha_frame
        sub_pha_lbl = ttk.Label(pha_frame, text="Ref.Φ with <T Range>:")
        sub_pha_txt1 = ttk.Entry(pha_frame, justify=tk.CENTER, width=8)
        self.sub_pha_txt1 = sub_pha_txt1
        sub_pha_txt2 = ttk.Entry(pha_frame, justify=tk.CENTER, width=8)
        self.sub_pha_txt2 = sub_pha_txt2
        sub_pha_lbl_from = ttk.Label(pha_frame, text="From")
        sub_pha_lbl_to = ttk.Label(pha_frame, text="To")
        reset_pha_btn = ttk.Button(pha_frame, text="Φ", width=2,
                                   command=partial(self.on_reset_pha, figure, ax_pha,
                                                   ax_pha_ylabel0))
        sub_pha_btn = ttk.Button(pha_frame, text=f"ΔΦ", width=3,
                                 command=partial(self.on_sub_pha, figure, ax_pha))
        # help info
        help_btn = ttk.Button(pha_frame, text="?", width=2,
                              command=self.on_help_figure_controls)
        #
        sub_pha_lbl.pack(side=tk.LEFT, padx=2, pady=2)
        sub_pha_lbl_from.pack(side=tk.LEFT, padx=2, pady=2)
        sub_pha_txt1.pack(side=tk.LEFT, padx=2, pady=2)
        sub_pha_lbl_to.pack(side=tk.LEFT, padx=2, pady=2)
        sub_pha_txt2.pack(side=tk.LEFT, padx=2, pady=2)
        sub_pha_btn.pack(side=tk.LEFT, padx=2, pady=2)
        reset_pha_btn.pack(side=tk.LEFT, padx=2, pady=2)
        help_btn.pack(side=tk.RIGHT, padx=2, pady=2)

        # initialize
        try:
            lw_sbox.set(ax_pha.get_lines()[0].get_lw())
        except:
            lw_sbox.set(1)
        fs_inc_sbox.set(0)

        # initialize the t range
        t_0 = self.find_first_valid_t()
        sub_pha_txt1.insert(0, str(t_0))
        sub_pha_txt2.insert(0, str(t_0 + 10))

    def on_rolling_wave(self, win_size: int, fig, ax_bcm, ax_pha, ax_mag):
        """ Apply rolling average to the waves.
        """
        win_size_s = str(win_size)
        is_roll_at_win_size = self.roll_var_map.get(win_size_s).get()
        if is_roll_at_win_size:
            # disable other roll_<win_size>_chkbox and
            # the chkbox for BCM/DBCM view, Norm/raw BCM
            other_state_s = "disabled"
            self._rolling_bcm_traces(ax_bcm, win_size)
        else:
            # enable other roll_<win_size>_chkbox
            # restore the chkbox for BCM/DBCM view, Norm/raw BCM
            # with the var variables
            other_state_s = "normal"
            self._restore_bcm_traces(ax_bcm)

        # update other rolling chkbox state
        for i, chkbox in self.roll_chkbox_map.items():
            if i == win_size_s:
                continue
            chkbox.config(state=other_state_s)
        # update the checkbox for DBCM/BCM view, norm/raw BCM data
        if other_state_s == "disabled":
            for o in (self.bcm_norm_toggle_chkbox, self.show_as_dbcm_chkbox):
                o.config(state=other_state_s)
        else:
            show_dbcm = self.show_as_dbcm_toggle_var.get()
            norm_bcm = self.bcm_norm_toggle_var.get()
            if not show_dbcm and not norm_bcm:
                state1, state2 = "normal", "normal"
            if show_dbcm and not norm_bcm:
                state1, state2 = "normal", "disabled"
            if not show_dbcm and norm_bcm:
                state1, state2 = "disabled", "normal"
            self.show_as_dbcm_chkbox.config(state=state1)
            self.bcm_norm_toggle_chkbox.config(state=state2)
        #
        fig.canvas.draw_idle()

    def _restore_bcm_traces(self, ax):
        """ Restore the traces before rolling averaging.
        """
        # normalized trace?
        is_norm = self.bcm_norm_toggle_var.get()
        for l in ax.get_lines():
            name = l.get_label()
            name = f"{name}_norm" if is_norm else name
            y0 = self.trace_data_map[name]
            l.set_ydata(y0)
        _auto_scale_y(ax)

    def _rolling_bcm_traces(self, ax, win_size: int):
        """ Apply rolling average to the BCM traces.
        """
        # normalized trace?
        is_norm = self.bcm_norm_toggle_var.get()
        for l in ax.get_lines():
            name = l.get_label()
            # since the same label is being used for original and the normalized trace
            # here needs to use different names in the trace_data_map.
            name = f"{name}_norm" if is_norm else name
            roll_name = f"{name}_{win_size}"
            # get and keep the original data, rolled one
            y0 = self.trace_data_map.setdefault(name, l.get_ydata())
            roll_y = self.trace_data_map.setdefault(roll_name, np.convolve(
                y0, np.ones(win_size) / win_size, mode='full')[:len(y0)])
            # only change the ydata
            l.set_ydata(roll_y)
        _auto_scale_y(ax)


    def save_bcm_plot(self, ax):
        """ Save BCM plot.
        """
        self.bcm_plots = []
        for l in ax.get_lines():
            self.bcm_plots.append((
                l.get_label(), l.get_lw(), l.get_ds(), l.get_color(),
                l.get_xdata(), l.get_ydata()
            ))

    def restore_bcm_plot(self, fig, ax):
        """ Restore BCM plot
        """
        ax.lines.clear()
        for name, lw, ds, color, xdata, ydata in self.bcm_plots:
            ax.plot(xdata, ydata, label=name, color=color, lw=lw, ds=ds)
        ax.legend()

    def save_dbcm_plot(self, ax):
        """ Save DBCM plot.
        """
        self.dbcm_plots = []
        for l in ax.get_lines():
            self.dbcm_plots.append((
                l.get_label(), l.get_lw(), l.get_ds(), l.get_color(),
                l.get_xdata(), l.get_ydata()
            ))

    def restore_dbcm_plot(self, fig, ax):
        """ Restore or plot DBCM plot.
        """
        ax.lines.clear()
        if self.dbcm_plots is None:
            # create new
            _, lw, ds, _, xdata, _ = self.bcm_plots[0]
            cc = cycle(_LINE_COLORS)
            for name, d in self.dbcm_df.items():
                ax.plot(xdata, d.to_numpy(), label=name, color=next(cc), lw=lw, ds=ds)
        else:
            for name, lw, ds, color, xdata, ydata in self.dbcm_plots:
                ax.plot(xdata, ydata, label=name, color=color, lw=lw, ds=ds)
        ax.legend()

    def on_plot_diff_bcm_traces(self, fig, ax):
        """ Switching the plot view between BCM and DBCM.
        """
        show_dbcm = self.show_as_dbcm_toggle_var.get()
        if show_dbcm:
            # disable norm bcm checkbox
            self.bcm_norm_toggle_chkbox.config(state="disabled")
            logger.info("Showing DBCM traces...")
            self.save_bcm_plot(ax)
            self.restore_dbcm_plot(fig, ax)
            self.bcm_ctrl_lbl.config(text="DBCM", foreground="red")
        else:
            # enable norm bcm checkbox
            self.bcm_norm_toggle_chkbox.config(state="normal")
            logger.info("Showing BCM traces...")
            self.save_dbcm_plot(ax)
            self.restore_bcm_plot(fig, ax)
            self.bcm_ctrl_lbl.config(text="BCM RAW", foreground="black")
        _auto_scale_y(ax)
        self.on_toggle_legends(fig)
        self.on_update_lw(fig)
        self.on_ds_changed(fig, None)
        self.on_update_fontsize(fig)
        # re-create vis control frame
        self._create_bcm_vis_btns(self.bcm_vis_ctrl_frame, fig, ax)

    def on_normalize_bcm_traces(self, bcm_fscale_map: dict, fig, ax):
        """ Normalize the BCM traces with FSCALE data for comparable.
        """
        to_norm = self.bcm_norm_toggle_var.get()
        if to_norm:
            # disable DBCM show checkbox
            self.show_as_dbcm_chkbox.config(state="disabled")
            logger.info(f"Normalizing BCM traces with FSCALE data)")
            for l, y0, sf in zip(ax.get_lines(), self.bcm_ydata0, self.bcm_fscales):
                logger.info(f"Scale raw BCM trace '{l.get_label()}' by {sf:.6g}X")
                l.set_ydata(y0 * sf)
            self.bcm_ctrl_lbl.config(text="BCM NORM", foreground="blue")
        else:
            # enable DBCM show checkbox
            self.show_as_dbcm_chkbox.config(state="normal")
            logger.info("Showing BCM raw traces...")
            for l, y0 in zip(ax.get_lines(), self.bcm_ydata0):
                l.set_ydata(y0)
            self.bcm_ctrl_lbl.config(text="BCM RAW", foreground="black")
        _auto_scale_y(ax)
        fig.canvas.draw_idle()

    def _create_bcm_vis_btns(self, frame, fig, ax):
        for w in frame.winfo_children():
            w.destroy()

        def on_show(name, curve, fig):
            curve.set_visible(self._curve_vis_map[name].get())
            fig.canvas.draw_idle()

        is_shown_dbcm_view = self.show_as_dbcm_toggle_var.get()
        if is_shown_dbcm_view:
            _text = "DBCM Trace"
            _start_trim = 5
        else:
            _text = "BCM Trace"
            _start_trim = 4

        lbl = ttk.Label(frame, text=_text, width=10)
        lbl.pack(side=tk.LEFT, padx=1)
        for l in ax.get_lines():
            name = l.get_label()
            v = self._curve_vis_map.setdefault(
                    name, tk.BooleanVar(value=BCM_TRACE_VIS_MAP.get(name, True)))
            chkbox = ttk.Checkbutton(frame, text=name[_start_trim:], variable=v,
                                     command=partial(on_show, name, l, fig))
            chkbox.pack(side=tk.LEFT, padx=1)
            if not v.get():
                on_show(name, l, fig)
                _auto_scale_y(ax)
                fig.canvas.draw_idle()
        # -> right button for layout
        layout_btn = ttk.Button(frame, text="Layout",
                                command=partial(self.on_show_layout, "BCM"))
        layout_btn.pack(side=tk.RIGHT, padx=1)

    def _create_bpm_vis_btns(self, frame, fig, ax_p, ax_m):
        def on_show(name, curve1, curve2, fig):
            is_shown = self._curve_vis_map[name].get()
            curve1.set_visible(is_shown)
            curve2.set_visible(is_shown)
            fig.canvas.draw_idle()

        lbl = ttk.Label(frame, text="BPM Trace", width=10)
        lbl.pack(side=tk.LEFT, padx=1)

        for l_p, l_m in zip(ax_p.get_lines(), ax_m.get_lines()):
            name = l_p.get_label()[:9]
            v = self._curve_vis_map.setdefault(
                    name, tk.BooleanVar(value=BPM_TRACE_VIS_MAP.get(name, True)))
            chkbox = ttk.Checkbutton(frame, text=name[4:], variable=v,
                                     command=partial(on_show, name, l_p, l_m, fig))
            chkbox.pack(side=tk.LEFT, padx=1)
            if not v.get():
                on_show(name, l_p, l_m, fig)
                _auto_scale_y(ax_p)
                _auto_scale_y(ax_m)
                fig.canvas.draw_idle()
        # -> right button for layout
        layout_btn = ttk.Button(frame, text="Layout",
                                command=partial(self.on_show_layout, "BPM"))
        layout_btn.pack(side=tk.RIGHT, padx=1)

    def on_show_layout(self, dev_type: str):
        """ Show the overview image for the layout of devices.
        """
        def _resize(evt):
            # resize
            w = popup.winfo_width()
            h = popup.winfo_height()
            w0, h0 = img.width, img.height
            new_w = w
            new_h = int(new_w * h0 / w0)
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.img_tk = ImageTk.PhotoImage(img_resized)
            img_lbl.config(image=self.img_tk)

        def _move_center(popup, parent, img_tk):
            # parent window position and size
            w, h = img_tk.width(), img_tk.height()
            px, py = parent.winfo_x(), parent.winfo_y()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            popup.geometry(f"{w}x{h}+{x}+{y}")

        popup = self._layout_win_map.get(dev_type)
        if popup is not None and popup.winfo_exists():
            img_tk = self._layout_imgtk_map[dev_type]
            _move_center(popup, self, img_tk)
            popup.lift()
            return

        if dev_type == "BCM":
            img_bytes = rc_bcm_image_bytes
        else:
            img_bytes = rc_bpm_image_bytes

        popup = tk.Toplevel()
        self._layout_win_map[dev_type] = popup
        popup.title(f"Schematic overview for: {dev_type}")
        popup.resizable(False, False)  # Enable resizing
        img_lbl = ttk.Label(popup, anchor=tk.CENTER)
        img_lbl.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        img = Image.open(img_bytes)
        img_tk = ImageTk.PhotoImage(img)
        img_lbl.config(image=img_tk)
        self._layout_imgtk_map[dev_type] = img_tk
        _move_center(popup, self, img_tk)
        # popup.bind("<Configure>", _resize)
        #popup.transient(self)
        #popup.grab_set()
        # popup.focus_force()

    def find_first_valid_t(self) -> int:
        """ Find the first t value that corresponding phase values are all valid for all phase
        traces.
        """
        if self.pha0_t is None:
            return 0
        t_0 = int(self.pha0_t[0])
        if not isinstance(self.pha0[0], np.ma.MaskedArray):
            # for opt data, just return the first T
            return t_0
        # otherwise, look for all traces
        try:
            idx = reduce(np.intersect1d, (np.where(~_arr.mask)[0] for _arr in self.pha0))
            t_0 = int(self.pha0_t[int(idx[0])])
            logger.debug(f"Found the common T where all phases are valid: {t_0}")
        except Exception as e:
            logger.error(f"Failed find the common T where all phases are valid: {e}")
        finally:
            return t_0

    def on_sub_pha(self, fig, ax):
        """ Subtract the PHA[i] for each trace, to show the relative waveform.
        """
        s1 = self.sub_pha_txt1.get()
        s2 = self.sub_pha_txt2.get()
        try:
            t1 = int(s1)
            t2 = int(s2)
        except ValueError as e:
            msg = f"Invalid time(s) in integer for computing reference phase value: {e}"
            logger.warning(msg)
            messagebox.showwarning(
                    title="Plot Self-diff Phases",
                    message=msg,
                    detail="Input integers of Time range [t1:t2] to compute the average "
                           "reference phase value for each trace"
            )
        else:
            # find the valid range of T
            t_range_valid = np.intersect1d(range(t1, t2 + 1), self.pha0_t)
            # find the indices in the original pha_t array
            idx = np.where(np.in1d(self.pha0_t, t_range_valid))[0]
            logger.info(f"Computing the average phase with PHA[{idx}]")

            for l, v in zip(ax.get_lines(), self.pha0):
                # the average phase reads in the selected range
                v0 = v[idx].mean()
                if np.ma.is_masked(v0):
                    msg = "The average phase readings in the selcted T range is --"
                    logger.warning(msg)
                    #messagebox.showwarning(
                    #    title="Plot Self-diff Phases",
                    #    message=msg,
                    #    detail="Adjust the T range to cover at least one valid phase value."
                    #)
                logger.info(f"Subtracting {v0:>6.3f} from trace {l.get_label():>13s}")
                l.set_ydata(v - v0)
            _auto_scale_y(ax)
            fs = ax.yaxis.label.get_fontsize()
            ax.set_ylabel("ΔΦ[$^o$] @ 80.5 MHz", fontsize=fs)
            fig.canvas.draw_idle()

    def on_reset_pha(self, fig, ax, ylabel0):
        """ Reset trace phase waveform to the original.
        """
        for l, v in zip(ax.get_lines(), self.pha0):
            l.set_ydata(v)
            logger.info(f"Reset trace {l.get_label():>13s}")
        _auto_scale_y(ax)
        fs = ax.yaxis.label.get_fontsize()
        ax.set_ylabel(ylabel0, fontsize=fs)
        fig.canvas.draw_idle()

    def on_toggle_legends(self, fig):
        """ Turn on/off legends.
        """
        checked = self.legend_toggle_var.get()
        for ax in fig.get_axes():
            lgd = ax.get_legend()
            if lgd:
                lgd.set_visible(checked)
        fig.canvas.draw_idle()

    def on_update_lw(self, fig):
        """ Update line width.
        """
        lw: float = float(self.lw_sbox.get())
        for ax in fig.get_axes():
            for l in ax.get_lines():
                l.set_lw(lw)
        fig.canvas.draw_idle()

    def on_ds_changed(self, fig, evt):
        """ Draw style changed.
        """
        ds = self.ds_var.get()
        for ax in fig.get_axes():
            for l in ax.get_lines():
                l.set_ds(ds)
        fig.canvas.draw_idle()

    def on_update_fontsize(self, fig):
        """ Inc/dec font sizes.
        """
        d_fs = float(self.fs_inc_sbox.get())
        new_fs = [i + d_fs for i in self.fs_init]
        for ax in fig.get_axes():
            # title
            ax.title.set_fontsize(new_fs[0])
            # text
            for i in ax.findobj(match=Text):
                i.set_fontsize(new_fs[0])
            # xylabels
            ax.xaxis.label.set_fontsize(new_fs[1])
            ax.yaxis.label.set_fontsize(new_fs[1])
            # xyticklabels
            for _tklbl in ax.xaxis.get_ticklabels() + ax.yaxis.get_ticklabels():
                _tklbl.set_fontsize(new_fs[2])
        fig.canvas.draw_idle()

    def on_help_bcm_controls(self, bcm_fscale_map: dict):
        """ Show the help messages for BCM/DBCM traces.
        """
        fscale_s = '\n'.join([f'{k} -> {v}' for k, v in bcm_fscale_map.items()])
        msg_text = f"""💡 The raw BCM traces are displayed initially.
💡 Check the 'Normalize' checkbox to scale the raw BCM traces with FSCALE factors (see the end).
💡 Uncheck the 'Normalize' checkbox to revert to the raw BCM view.
💡 Check the 'DBCM' checkbox to switch to the view of DBCM traces.
💡 Uncheck the 'DBCM' checkbox to switch to the view of raw BCM traces.
💡 The DBCM view is only checkable when 'Normalize' is not checked.
💡 The FSCALE factors used in current dataset: {fscale_s}"""
        messagebox.showinfo(title="FigureWindow - Help (BCM/DBCM)",
                message="BCM/DBCM Traces Explained:",
                detail=msg_text,
                type=messagebox.OK)

    def on_help_figure_controls(self):
        """ Show the help messages for the controls.
        """
        msg_text = """💡 Diff mode: each trace - Ref.Φ, click ΔΦ button
💡 Original mode: original trace, click Φ button

Compute the reference phase (Ref.Φ) of each trace requires the input of time (T) range
in the two entries, each is an integer as time in μs, put them in ascending
order from left to right; then the time range is used to find the phase range to
compute the average values as the references.

The two values of T range are initialized with the first valid time (T1) and the 10th after
it (T2). Note that for the raw dataset, the initial values are computed such that for all
traces, at the assigned T1, phase values are all valid; otherwise, fall back to
the first element of the time array."""
        messagebox.showinfo(title="FigureWindow - Help (BPM Phase)",
                message="Presenting Phase Traces: Diff & Original Modes",
                detail=msg_text,
                type=messagebox.OK)


def _auto_scale_y(ax):
    ax.relim(visible_only=True)
    ax.autoscale(axis='y')


def on_auto_y(fig):
    """ Auto Y scale for all axes.
    """
    for ax in fig.get_axes():
        _auto_scale_y(ax)
    fig.canvas.draw_idle()


def sync_xlimits(fig, ref_ax):
    """ Set the xlimits for all axes with the xlimit from ref_ax.
    """
    xlimit = ref_ax.get_xlim()
    for ax in fig.get_axes():
        ax.set_xlim(xlimit)
    fig.canvas.draw_idle()


def configure_styles(root: tk.Tk, theme_name: str = "breeze"):
    try:
        import ttkthemes
    except ModuleNotFoundError:
        root.style = ttk.Style()
        root.style.theme_use('default')
        logger.debug("Configure styles with theme 'default'.")
    else:
        root.style = ttkthemes.ThemedStyle()
        root.style.theme_use(theme_name)
        logger.debug(f"Configure styles with theme '{theme_name}'.")
    finally:
        # adjust the row height of Treeview
        _font = tk.font.nametofont("TkTextFont")
        # _monofont = tk.font.nametofont("TkFixedFont")
        # _monofontfamily = _monofont.actual()['family']
        # _monofontsize = _monofont.actual()['size']
        # font_family = _font.actual()['family']
        # font_size = _font.actual()['size']
        line_height = _font.metrics()['linespace']
        # Treeview
        root.style.configure("Treeview", rowheight=line_height)
        logger.debug(f"Configure styles: adjust row height of treeview.")
        # root.style.configure("Treeview", font=(_monofontfamily, _monofontsize))
        # logger.debug(f"Configure styles: set treeview font to {_monofontfamily}, {_monofontsize}")


if __name__ == "__main__":
    import matplotlib
    matplotlib.use('tkagg')

    import tkinter as tk

    import matplotlib.pyplot as plt
    import numpy as np

    # with root
    root = tk.Tk()
    # without root
    # root = None

    figs = []
    for i in range(4):
        fig, ax = plt.subplots()
        ax.plot(np.arange(10), np.random.random(10))
        figs.append((fig, f"figure-{i}"))

    app = FigureWindow(figs, "Figures", (2, 5), parent=root)
    if root is None:
        app.mainloop()
    else:
        root.mainloop()
