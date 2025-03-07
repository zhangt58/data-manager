#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk


class FigureWindow(tk.Tk):
    # Present figures in a Tkinter GUI,
    # keywords: fig_dpi
    def __init__(self, figures: list[tuple],
                 window_title: str, grid: tuple[int, int],
                 padx: int = 5, pady: int = 5, notes: str = "",
                 **kws):
        super().__init__()

        # styles
        configure_styles(self, theme_name="arc")
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
        bottom_frame.pack(side="bottom", fill=tk.X)

        # notes area
        notes_text = tk.Text(bottom_frame, height=3)
        notes_text.insert("1.0", notes)
        notes_text.config(state="disable")
        notes_text.pack(side="left", fill=tk.X, pady=pady, expand=True)
        # quit button
        quit_btn = ttk.Button(bottom_frame, text="Quit", command=self.quit)
        quit_btn.pack(side="right", fill=tk.X, pady=pady, padx=padx)

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
        #
        # Main frame style
        root.style.configure("TFrame", background="#f0f0f0")

        # Control frame style
        root.style.configure("ControlFrame.TFrame", background="#e0e0e0", relief="raised",
                             borderwidth=1)

        # Label frame style
        root.style.configure("TLabelframe", background="#f0f0f0", relief="groove",
                             borderwidth=2)

        # Label frame label style
        root.style.configure("TLabelframe.Label", font=(font_family, font_size + 10, "bold"),
                             foreground="#333333", background="#f0f0f0")

        # Style controls frame
        root.style.configure("StyleControls.TLabelframe", background="#e8e8e8", relief="ridge",
                             borderwidth=2)

        root.style.configure("StyleControls.TLabelframe.Label", font=(font_family, font_size, "bold"),
                             foreground="#444444", background="#e8e8e8")

        # Label style
        root.style.configure("TLabel", background="#f0f0f0", font=(font_family, font_size))

        # Button style
        root.style.configure("TButton", font=(font_family, font_size))

        # Combobox style
        root.style.configure("TCombobox", font=(font_family, font_size))
    else:
        root.style = ttkthemes.ThemedStyle()
        root.style.theme_use(theme_name)
    finally:
        # adjust the row height of Treeview
        _font = tk.font.nametofont("TkTextFont")
        font_family = _font.actual()['family']
        font_size = _font.actual()['size']
        line_height = _font.metrics()['linespace']

        # font_family = "Cantarell"
        # font_size = 10

        # Treeview
        root.style.configure("Treeview", rowheight=line_height)


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import numpy as np

    figs = []
    for i in range(4):
        fig, ax = plt.subplots()
        ax.plot(np.arange(10), np.random.random(10))
        figs.append(fig)

    print(figs)
    app = FigureWindow(figs, "Figures", (2, 5))
    app.mainloop()

