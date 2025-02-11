#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from datetime import datetime
from functools import partial
import cothread
from cothread.catools import camonitor, caget
from _init import data_rootdir, logger


def gen_names(name):
    ts_pv = f"{name}:wv_t0"
    pvs = [f"{name}:wv_beamst"]
    alias = [f"{name}:BEAMST"]
    for i in range(1, 5):
        pvs.append(f"{name}:wv_pha{i}")
        pvs.append(f"{name}:wv_mag{i}")
        alias.append(f"{name}:PHA{i}")
        alias.append(f"{name}:MAG{i}")
    return ts_pv, pvs, alias


def gen_pvs(bpm_name: str):
    pvs = []
    for i in range(1, 5):
        pvs.append(f"{name}:wv_pha{i}")
        pvs.append(f"{name}:wv_mag{i}")


data_dir = data_rootdir.joinpath("BPM")

t_delay = 5

pv_fault_id = "ACS_DIAG:MPS_FIND:FAULT_ID_RD"
def on_fetch(bpm_name, pv_names, index, value):
    logger.info(
        f"To fetch BPM {bpm_name} waveform in {t_delay}s ... {value}")
    ts = datetime.fromtimestamp(value)
    def f():
        logger.debug(f"Waiting ... ({t_delay}s)")
        cothread.Sleep(t_delay)
        logger.debug(f"Waiting ... done")
        *wf_data, ftid = caget(pv_names + [pv_fault_id])
        subdir = ts.strftime("%Y%m%dT%H%M")
        fn = f"{bpm_name}-{ts.strftime('%Y%m%dT%H%M%S-%f')}_{ftid}.h5"
        outpath = data_dir.joinpath(subdir, fn)
        outpath.parent.mkdir(exist_ok=True, parents=True)
        df = pd.DataFrame.from_records(wf_data, index=index)
        df['PV'] = pv_names
        df.to_hdf(outpath, key="data", complevel=9, complib='bzip2')
        logger.info(f"Saved data to {fn}")
    cothread.Spawn(f)


names = [
        "FS1_CSS:BPM_D2212",
        "FS1_CSS:BPM_D2223",
        "FS1_CSS:BPM_D2248",
        "FS1_CSS:BPM_D2278",
        "FS1_CSS:BPM_D2313",
]

for name in names:
    ts_pv, pvnames, index = gen_names(name)
    camonitor(ts_pv, partial(on_fetch, name[-5:], pvnames, index))

cothread.WaitForQuit()
