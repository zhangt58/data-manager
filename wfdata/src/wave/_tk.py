#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from functools import partial
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.text import Text

from ._log import logger


class FigureWindow(tk.Toplevel):
    # Present figures in a Tkinter GUI,
    # keywords: fig_dpi, theme_name
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

        # layout figures
        for i, (fig, fig_title) in enumerate(figures):
            irow, icol = i // ncols, i % ncols
            self.place_figure(main_frame, fig, fig_title, irow, icol, padx, pady,
                              fig_dpi=kws.get('fig_dpi', None))

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
                     padx: int = 5, pady: int = 5, fig_dpi: int = None):
        frame = ttk.LabelFrame(parent, text=title, borderwidth=1, relief=tk.GROOVE)
        frame.grid(row=row, column=col, padx=padx, pady=pady, sticky="nsew")

        # tools: toolbar + controls
        #
        tools_frame = ttk.Frame(frame)
        tb_frame = ttk.Frame(tools_frame)
        ctrl_frame = ttk.Frame(tools_frame)
        #
        tools_frame.pack(fill=tk.X, padx=2, pady=2)
        tb_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        ctrl_frame.pack(side=tk.RIGHT)

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
        misc_frame.pack(fill=tk.X, padx=2, pady=2, side=tk.LEFT, expand=True)
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

        # --------------
        # | ctrl_frame |
        # --------------
        # | sync-1,2,3 |
        # | [i] -PHA[i]|  # each phase trace - i-th value to display the relative trend
        sync_frame = ttk.Frame(ctrl_frame)
        sync_frame.pack(side=tk.TOP)
        pha_frame = ttk.Frame(ctrl_frame)
        pha_frame.pack(side=tk.BOTTOM)
        ax_pha = None
        self.pha0: list = []
        i = 1
        sync_frame_w = 0
        sync_lbl = ttk.Label(sync_frame, text="↔", width=2)
        sync_lbl.pack(side=tk.LEFT, padx=1)
        sync_frame_w += 2
        for ax in figure.get_axes():
            if ax.get_ylabel() == "NPERMIT":
                continue
            ax.text(-0.05, 1.05, f"{i}", transform=ax.transAxes,
                    size=self.fs_init[0],
                    bbox=dict(facecolor='w', alpha=0.9, edgecolor='k'))
            if 'Phi' in ax.get_ylabel():
                ax_pha = ax
                ax_pha_ylabel0: str = ax.get_ylabel()
                self.pha0 = [l.get_ydata() for l in ax.get_lines()]
            sync_btn = ttk.Button(sync_frame, text=f"X{i}", width=3,
                                  command=partial(sync_xlimits, figure, ax))
            sync_btn.pack(side=tk.LEFT, padx=1)
            sync_frame_w += 4
            i += 1
        # add a button to adjust auto scale Y limits
        auto_y_btn = ttk.Button(sync_frame, text="↕", width=2,
                                command=partial(on_auto_y, figure))
        auto_y_btn.pack(side=tk.LEFT, padx=1)
        sync_frame_w += 4

        # pha_frame
        sub_pha_lbl = ttk.Label(pha_frame, text="Φ-idx", width=5)
        sub_pha_txt = ttk.Entry(pha_frame, width=sync_frame_w + 1 - (5 + 2 + 3 + 4 * 1),
                                justify=tk.CENTER)
        sub_pha_txt.insert(0, "0")
        self.sub_pha_txt = sub_pha_txt
        reset_pha_btn = ttk.Button(pha_frame, text="Φ", width=2,
                                   command=partial(self.on_reset_pha, figure, ax_pha,
                                                   ax_pha_ylabel0))
        sub_pha_btn = ttk.Button(pha_frame, text=f"ΔΦ", width=3,
                                 command=partial(self.on_sub_pha, figure, ax_pha))
        #
        sub_pha_lbl.pack(side=tk.LEFT, padx=1, pady=2)
        sub_pha_txt.pack(side=tk.LEFT, padx=1, pady=2)
        sub_pha_btn.pack(side=tk.LEFT, padx=1, pady=2)
        reset_pha_btn.pack(side=tk.RIGHT, padx=1, pady=2)

        # initialize
        lw_sbox.set(ax_pha.get_lines()[0].get_lw())
        fs_inc_sbox.set(0)

    def on_sub_pha(self, fig, ax):
        """ Subtract the PHA[i] for each trace, to show the relative waveform.
        """
        s = self.sub_pha_txt.get()
        try:
            idx = int(s)
        except ValueError as e:
            msg = f"Invalid index of Phase waveform: {e}"
            logger.error(msg)
            messagebox.showwarning(
                    title="Plot Self-diff Phases",
                    message=msg,
                    detail="Input an integer >= 0 as the index to select the "
                           "reference phase value for each trace"
            )
        else:
            logger.debug(f"Subtract PHA[{idx}] from each trace.")
            for l, v in zip(ax.get_lines(), self.pha0):
                l.set_ydata(v - v[idx])
            _auto_scale_y(ax)
            fs = ax.yaxis.label.get_fontsize()
            ax.set_ylabel("ΔΦ[$^o$] @ 80.5 MHz", fontsize=fs)
            fig.canvas.draw_idle()

    def on_reset_pha(self, fig, ax, ylabel0):
        """ Reset trace phase waveform to the original.
        """
        for l, v in zip(ax.get_lines(), self.pha0):
            l.set_ydata(v)
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
