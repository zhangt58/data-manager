#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cmath
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from functools import partial
from typing import Union

from ._log import logger


def _process_format_v0(store):
    logger.info(f"Reading {store.filename} per format v0")
    try:
        # BCM
        all_keys = store.keys()
        bcm_dfs = []
        for i in ("DATA", "NPERMIT"):
            k = f"/BCM/{i}"
            if k not in all_keys:
                continue
            bcm_dfs.append(store[k])
    except Exception as e:
        logger.warning(f"Error processing BCM {store.filename}: {e}")
        return None, None
    try:
        # BPM
        bpm_dfs = []
        for i in ("MAG", "PHA"):
            k = f"/BPM/{i}"
            if k not in all_keys:
                continue
            bpm_dfs.append(store[k])
        #
        bpm_cols = store['/INFO/PV'].filter(regex=r'(BPM_D[0-9]{4}).*', axis=0)
        bpm_names = bpm_cols.index.str.replace(r"(BPM_D[0-9]{4}).*", r"\1", regex=True).unique().to_list()
        #
    except Exception as e:
        logger.warning(f"Error processing BPM {store.filename}: {e}")
        return None, None
    #
    return bcm_dfs + bpm_dfs, bpm_names


def _process_format_v1(store):
    logger.info(f"Reading {store.filename} per format v1")
    df_t0 = store['/t0']
    df_grp = store['/grp']
    df_info = store['/info']
    df_bcm = store['/bcm'].T
    df_bpm = store['/bpm'].T

    # BCM
    bcm_grps = df_grp.index[df_grp.index.str.startswith('BCM')]
    bcm_dfs = []
    try:
        for bcm_grp in bcm_grps:
            # print(f"{bcm_grp} T0: {df_t0[bcm_grp]}")
            _bcm_df = df_bcm[df_grp[bcm_grp]]
            _t_idx = pd.date_range(start=df_t0[bcm_grp], periods=_bcm_df.shape[0], freq='us')
            bcm_dfs.append(_bcm_df.set_index(_t_idx))
    except Exception as e:
        logger.warning(f"Error processing BCM {store.filename}: {e}")
        return None, None

    # BPM
    bpm_grps = df_grp.index[~df_grp.index.str.startswith('BCM')]
    bpm_dfs = []
    try:
        for bpm_grp in bpm_grps:
            # print(f"{bpm_grp} T0: {df_t0[bpm_grp]}")
            _bpm_df = df_bpm[df_grp[bpm_grp]]
            _t_idx = pd.date_range(start=df_t0[bpm_grp], periods=_bpm_df.shape[0], freq='us')
            bpm_dfs.append(_bpm_df.set_index(_t_idx))
    except Exception as e:
        logger.warning(f"Error processing BPM {store.filename}: {e}")
        return None, None
    #
    bpm_names = [f"BPM_{i}" for i in bpm_grps]
    #
    return bcm_dfs + bpm_dfs, bpm_names


def read_data(filepath: str,
              t_range: Union[tuple[int, int], None] = (-800, 400)):
    """ Read and consolidate dataset.
    """
    with pd.HDFStore(filepath, mode="r") as store:
        if '/grp' in store.keys():
            dfs, bpm_names = _process_format_v1(store)
        else:
            dfs, bpm_names = _process_format_v0(store)
        #
    if dfs is None:
        logger.warning("Error reading data.")
        return None, ""

    df_all = pd.concat(dfs, axis=1).sort_index(axis=1)

    npermit_names = ('BCM4_NPERMIT', 'BCM5_NPERMIT', 'BCM5_NPERMIT')
    if all(i not in df_all for i in npermit_names):
        logger.warning("No NPERMIT signals, cannot figure out T trip.")
        return None, ""

    # find the first index loc (int) that npermit goes high (1)
    # find the first occurence of BCM?_NPERMIT that with high bits, and drop others
    # if none is found, throw out error
    npermit_col: str = None
    for c in npermit_names:
        if c not in df_all.columns:
            continue
        if df_all[c].sum() == 0:
            continue
        npermit_col = c

    if npermit_col is not None:
        t0_idx: int = (df_all[npermit_col]==1.0).argmax()
        # only keep one column for npermit
        for c in npermit_names:
            if c in df_all.columns and c != npermit_col:
                df_all.pop(c)
    else:
        logger.warning("No high bit signals in NPERMITs, cannot figure out T trip.")
        return None, ""

    t0_val: pd.Timestamp = df_all.index[t0_idx]
    t0_str: str = t0_val.to_pydatetime().isoformat()

    # the dataframe-of-interest
    if t_range is not None:
        df = df_all.iloc[t0_idx + t_range[0]:t0_idx + t_range[1], :].copy()
    else:
        df = df_all.copy()
    df['t_us'] = (df.index - t0_val) / pd.Timedelta(1, "us")
    # process BPM MAG and PHA columns
    # bpm_cols = store['INFO/PV'].filter(regex=r'(BPM_D[0-9]{4}).*', axis=0)
    # bpm_names = bpm_cols.index.str.replace(r"(BPM_D[0-9]{4}).*", r"\1", regex=True).unique().to_list()
    new_cols = []
    for name in bpm_names:
        new_cols.extend([f"{name}-MAG", f"{name}-PHA"])
    df[new_cols] = df.apply(partial(process_bpm_cplx, bpm_names), axis=1).tolist()
    # drop BPM_D####:MAG/PHAi columns
    cols_to_drop = df.filter(regex=r"BPM_.*[1-4]{1}$").columns
    df.drop(columns=cols_to_drop, inplace=True)
    return df, t0_str


def process_bpm_cplx(names: list[str], row: pd.Series):
    """ Process the BPM complex signals, merge 1,2,3,4 into one.
    """
    # PHA is measured at 80.5 MHz, but value at 161 MHz should be used,
    # i.e. actual phase is PHA * 2
    mag_pha = []
    for name in names:
        cmpl = 0
        for i in range(1, 5):
            magi = row[f"{name}:MAG{i}"]
            phai = row[f"{name}:PHA{i}"]
            cmpl += magi * np.exp(-1j * phai * 2 * np.pi / 180.0)
        mag_pha.extend([abs(cmpl), cmath.phase(cmpl) * 90 / np.pi])
    return mag_pha


def _plot_no_data(ax, reason: str = "NO DATA"):
    ax.annotate(reason, (0.5, 0.5), xycoords='axes fraction',
                color="gray", fontsize=28, ha='center', va='center')


def plot(df: pd.DataFrame, t0: str, title: str):

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 9), dpi=110)

    xylabel_fontdict = {"size": 14, "family": "Cantarell"}
    xyticks_fontdict = {"size": 13, "family": "Cantarell"}
    grid_color = "#7F8C8D"

    # BCM
    bcm_cols = [c for c in df.columns if c.startswith("BCM") and not c.endswith('NPERMIT')]
    if bcm_cols:
        if df[bcm_cols].isna().all().all():
            _plot_no_data(ax1, "All NaN")
        else:
            df.plot(x='t_us', y=bcm_cols, ax=ax1, xlabel="")
    else:
        # show NO DATA
        _plot_no_data(ax1)

    ax1.set_ylabel("Intensity [a.u.]")
    ax1.set_title(title, fontsize=16, fontfamily="Cantarell")

    ax1r = ax1.twinx()
    npermit_col = [c for c in df.columns if c.endswith('NPERMIT')][0]
    df.plot(x='t_us', y=npermit_col, c='#2C3E50', ls='-.', lw=1, ax=ax1r,
            label=npermit_col,
            fontsize=14, ylim=(-0.2, 1.2))
    ax1r.set_ylabel("NPERMIT")
    ax1r.legend(loc="lower left")

    # BPM
    bpm_amp_cols = [c for c in df.columns if 'MAG' in c]
    bpm_pha_cols = [c for c in df.columns if 'PHA' in c]
    if bpm_amp_cols:
        if df[bpm_amp_cols].isna().all().all():
            _plot_no_data(ax2, "All NaN")
        else:
            df.plot(x='t_us', y=bpm_amp_cols, ax=ax2, xlabel="")
    else:
        _plot_no_data(ax2)
    if bpm_pha_cols:
        if df[bpm_pha_cols].isna().all().all():
            _plot_no_data(ax3, "All NaN")
        else:
            df.plot(x='t_us', y=bpm_pha_cols, ax=ax3)
    else:
        _plot_no_data(ax3)
    ax2.set_ylabel("Intensity [a.u.]")
    ax3.set_xlabel("Time $[\mu s]$")
    ax3.set_ylabel("$\Phi [^o]$ @ 80.5 MHz")
    ax3.annotate(f"$T_0$ = {t0}", (0, -0.3), xycoords='axes fraction',
                 fontfamily="monospace", fontsize=12)

    for iax in (ax1, ax2, ax3):
        iax.minorticks_on()
        iax.grid(which='minor', ls=':', c=grid_color, alpha=0.5)
        iax.grid(which='major', ls='-', c=grid_color, alpha=0.8)

    for iax in (ax1, ax1r, ax2, ax3):
        for tklbl in iax.get_xticklabels() + iax.get_yticklabels():
            tklbl.set_fontsize(xyticks_fontdict['size'])
            tklbl.set_fontfamily(xyticks_fontdict['family'])
        for u in ('x', 'y'):
            lbl_o = getattr(iax, f'{u}axis').label
            lbl_o.set_fontsize(xylabel_fontdict['size'])
            lbl_o.set_fontfamily(xylabel_fontdict['family'])
    #plt.show()
    return fig


if __name__ == "__main__":
    from pathlib import Path

    fault_id = "23635"
    filepath = Path(f"test1/{fault_id}.h5")

    df, t0_str = read_data(filepath)

    fig = plot(df, t0_str, f"MPS fault ID: {fault_id}")
    fig.tight_layout()
    for typ in ("png", "pdf"):
        fig_outpath = filepath.parent.joinpath(f"{fault_id}.{typ}")
        fig.savefig(fig_outpath)
    plt.show()

