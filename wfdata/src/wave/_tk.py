#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

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
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True)

        nrows, ncols = grid
        for i in range(nrows):
            frame.rowconfigure(i, weight=1)
        for j in range(ncols):
            frame.columnconfigure(j, weight=1)

        # layout figures
        for i, (fig, fig_title) in enumerate(figures):
            irow, icol = i // ncols, i % ncols
            self.place_figure(frame, fig, fig_title, irow, icol, padx, pady,
                              fig_dpi=kws.get('fig_dpi', None))

        # bottom area
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
        frame = ttk.LabelFrame(parent, text=title)
        frame.grid(row=row, column=col, padx=padx, pady=pady, sticky="nsew")

        fig_frame = ttk.Frame(frame)
        fig_frame.pack(fill=tk.BOTH, expand=True)

        # change figure dpi
        if fig_dpi is not None:
            figure.set_dpi(fig_dpi)
        #
        canvas = FigureCanvasTkAgg(figure, master=fig_frame)
        canvas.draw_idle()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tb_frame = ttk.Frame(frame)
        tb_frame.pack(fill=tk.X)
        tb = NavigationToolbar2Tk(canvas,tb_frame)
        tb.update()


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
        # font_family = _font.actual()['family']
        # font_size = _font.actual()['size']
        line_height = _font.metrics()['linespace']
        # Treeview
        root.style.configure("Treeview", rowheight=line_height)
        logger.debug(f"Configure styles: adjust row height of treeview.")


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
