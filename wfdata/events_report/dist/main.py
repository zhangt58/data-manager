#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import pygwalker as pyg
from pathlib import Path
import sys

from _build import build_page


def main():
    trip_events_file = Path(sys.argv[1])
    trip_info_file = Path(sys.argv[2])

    df = pd.read_csv(trip_events_file, delimiter=";")
    df_info = pd.read_hdf(trip_info_file)[
        ["ID", "Energy", "devices", "t window", "threshold"]].rename(columns={
            "ID": "Fault_ID",
            "devices": "Devices",
            "t window": "T Window",
            "threshold": "Threshold",
        })

    df_all = pd.merge(df, df_info, on="Fault_ID", how="outer").sort_values(
            "Fault_ID", ascending=False).reset_index(drop=True)
    df_all = df_all[~df_all['Type'].isin(['CHOPPER MITIGATION', 'MITIGATION'])]
    df_all['Energy'] = df_all['Energy'].round(3)
    df_all['Time'] = pd.to_datetime(df_all['Time'])

    # df_238U = df_all[df_all["Ion"]=="238U"]
    # df_238U_mtca = df_238U[df_238U["Type"]=="MTCA"].dropna()

    if sys.argv[3] == "show":
        walker = pyg.walk(df_all, default_tab="data")
        walker.show()
    else:
        html = pyg.to_html(df_all, default_tab="data", theme_key="g2")
        with open("data_view.html", "w") as fp:
            fp.write(html)
        build_page("data_view.html", "mps-faults.html")


if __name__ == "__main__":
    main()
