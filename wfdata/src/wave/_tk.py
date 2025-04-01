#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import tkinter as tk
from functools import (
    partial,
    reduce
)
from tkinter import (
    ttk,
    messagebox
)
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)
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

        # tools frame:
        # |toolbar | X-Axis |
        # |phase   | Y-Axis |
        # figure frame
        # misc frame
        #
        tools_frame = ttk.Frame(frame)
        tools_frame.pack(fill=tk.X, padx=2, pady=2)
        tools_frame.columnconfigure(0, weight=1)
        tools_frame.columnconfigure(1, weight=0)

        tb_frame = ttk.Frame(tools_frame)
        xaxis_frame = ttk.Frame(tools_frame)
        tb_frame.grid(row=0, column=0, sticky="ew")
        xaxis_frame.grid(row=0, column=1, sticky="ew")
        #
        pha_frame = ttk.Frame(tools_frame)
        yaxis_frame = ttk.Frame(tools_frame)
        pha_frame.grid(row=1, column=0, sticky="ew")
        yaxis_frame.grid(row=1, column=1, sticky="ew")

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

        # phase frame (variables)
        ax_pha = None
        # a list of np.ndarray/np.ma.MaskedArray of phase values
        self.pha0: list[Union[np.ndarray, np.ma.MaskedArray]] = []
        # time array of phase figure
        self.pha0_t: np.ndarray = None

        # xaxis frame
        i = 1
        sync_lbl = ttk.Label(xaxis_frame, text="Sync ↔")
        sync_lbl.pack(side=tk.LEFT, padx=1)
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
                if len(ax.get_lines()) != 0:
                    self.pha0_t = ax.get_lines()[0].get_xdata()
                else:
                    self.pha0_t = None
                # print(type(self.pha0[0]), self.pha0[0][:100])
            sync_btn = ttk.Button(xaxis_frame, text=f"{i}", width=3,
                                  command=partial(sync_xlimits, figure, ax))
            sync_btn.pack(side=tk.LEFT, padx=1)
            i += 1
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

    def on_help_figure_controls(self):
        """ Show the help messages for the controls.
        """
        msg_text = """* Diff mode: each trace - Ref.Φ, click ΔΦ button
* Original mode: original trace, click Φ button

Compute the reference phase (Ref.Φ) of each trace requires the input of time (T) range
in the two entries, each is an integer as time in μs, put them in ascending
order from left to right; then the time range is used to find the phase range to
compute the average values as the references.

The two values of T range are initialized with the first valid time (T1) and the 10th after
it (T2). Note that for the raw dataset, the initial values are computed such that for all
traces, at the assigned T1, phase values are all valid; otherwise, fall back to
the first element of the time array."""
        messagebox.showinfo(title="FigureWindow - Help",
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
