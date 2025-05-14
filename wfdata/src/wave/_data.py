#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cmath
import json
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Union

from ._log import logger

DEFAULT_MPL_FONT_SIZE = mpl.rcParams['font.size']
DEFAULT_MPL_FONT_FAMILY = mpl.rcParams['font.family']
DEFAULT_MPL_FIG_DPI = mpl.rcParams['figure.dpi']

BCM_FSCALE_NAME_MAP = {
    "BCM_D0989": "FE_LEBT:BCM_D0989:FSCALE_CSET",
    "BCM_D1120": "FE_MEBT:BCM_D1120:FSCALE_CSET",
    "BCM_D2183": "FS1_CSS:BCM_D2183:FSCALE_CSET",
    "BCM_D2264": "FS1_CSS:BCM_D2264:FSCALE_CSET",
    "BCM_D2519": "FS1_BMS:BCM_D2519:FSCALE_CSET",
    "BCM_D2675": "FS1_BMS:BCM_D2675:FSCALE_CSET",
    "BCM_D3936": "FS2_BTS:BCM_D3936:FSCALE_CSET",
    "BCM_D4169": "FS2_BBS:BCM_D4169:FSCALE_CSET",
    "BCM_D5521": "BDS_BTS:BCM_D5521:FSCALE_CSET",
    "BCM_D5789": "BDS_FFS:BCM_D5789:FSCALE_CSET",
    "BCM_D1120c": "FE_COPY:BCM_D1120:FSCALE_CSET",
}

# the default BCM/DBCM trace visibility
BCM_TRACE_VIS_MAP = {
    "BCM_D0989": True,
    "BCM_D1120": True,
    "BCM_D2183": True,
    "BCM_D2264": True,
    "BCM_D2519": True,
    "BCM_D2675": True,
    "BCM_D3936": True,
    "BCM_D4169": False,
    "BCM_D5521": True,
    "BCM_D5789": True,
    "BCM_D1120c": False,
    # DBCM
    "DBCM_LS1TRANS": True,
    "DBCM_CHRGSTAT": True,
    "DBCM_STRPEFF": True,
    "DBCM_LS2TRANS": True,
    "DBCM_LS3TRANS": False,
    "DBCM_LINACBDS": True,
    "DBCM_LINACTGT": True,
}

# the BPM traces to hide
BPM_TRACE_VIS_MAP = {
    "BPM_D2466": False
}

# the datafiles (v1) with datetime before defined should be fixed
# BCM_D1120 -> BCM_D1120c
# BCM_D2183 -> BCM_D0989
DATE_PRIOR_FIX = datetime(year=2025, month=5, day=12, hour=10)


def _process_format_v0(store):
    logger.debug(f"Processing {store.filename} (v0 raw)...")
    try:
        # BCM
        all_keys = store.keys()
        bcm_dfs = []
        for i in ("DATA", "NPERMIT"):
            k = f"/BCM/{i}"
            if k not in all_keys:
                continue
            bcm_dfs.append(
                store[k].rename(
                    columns={"BCM_D1120": "BCM_D1120c", "BCM_D2183": "BCM_D0989"})
                )
    except Exception as e:
        logger.error(f"Error processing BCM {store.filename}: {e}")
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
        logger.error(f"Error processing BPM {store.filename}: {e}")
        return None, None
    #
    logger.debug(f"Processing {store.filename} (v0 raw)...done!")
    return bcm_dfs + bpm_dfs, bpm_names


def _process_format_v1(store):
    logger.debug(f"Processing {store.filename} (v1 raw)...")
    df_t0 = store['/t0']
    df_grp = store['/grp']
    # df_info = store['/info']
    df_bcm = store['/bcm'].T
    df_bpm = store['/bpm'].T
    # BCM FSCALE
    df_bcm_fscale = store['/bcm_fscale'] if '/bcm_fscale' in store else None

    fix_bcm = _to_fix_bcm_dateset(store.filename)

    # BCM
    bcm_grps = df_grp.index[df_grp.index.str.startswith('BCM')]
    bcm_dfs = []
    try:
        for bcm_grp in bcm_grps:
            # print(f"{bcm_grp}: {df_grp[bcm_grp]}")
            if any(i not in df_bcm for i in df_grp[bcm_grp]):
                logger.warning(f"Missing data: {df_grp[bcm_grp]} in {store.filename}")
                continue
            if fix_bcm:
                _bcm_df = df_bcm[df_grp[bcm_grp]].rename(
                        columns={"BCM_D1120": "BCM_D1120c", "BCM_D2183": "BCM_D0989"})
            else:
                _bcm_df = df_bcm[df_grp[bcm_grp]]
            _t_idx = pd.date_range(start=df_t0[bcm_grp], periods=_bcm_df.shape[0], freq='us')
            bcm_dfs.append(_bcm_df.set_index(_t_idx))
        if df_bcm_fscale is not None:
            # a little bit hacking
            logger.info("Attaching BCM FSCALE data to the first BCM dataset...")
            bcm_dfs[0].attrs['fscale'] = df_bcm_fscale[0].to_dict()
    except Exception as e:
        logger.error(f"Error processing BCM {store.filename}: {e}")
        return None, None

    # BPM
    bpm_grps = df_grp.index[~df_grp.index.str.startswith('BCM')]
    bpm_dfs = []
    try:
        for bpm_grp in bpm_grps:
            # print(f"{bpm_grp}: {df_grp[bpm_grp]}")
            if any(i not in df_bpm for i in df_grp[bpm_grp]):
                logger.warning(f"Missing data: {df_grp[bpm_grp]} in {store.filename}")
                bpm_grps = bpm_grps.drop(bpm_grp)
                continue
            _bpm_df = df_bpm[df_grp[bpm_grp]]
            _t_idx = pd.date_range(start=df_t0[bpm_grp], periods=_bpm_df.shape[0], freq='us')
            bpm_dfs.append(_bpm_df.set_index(_t_idx))
    except Exception as e:
        logger.error(f"Error processing BPM {store.filename}: {e}")
        return None, None
    #
    bpm_names = [f"BPM_{i}" for i in bpm_grps]
    #
    logger.debug(f"Processing {store.filename} (v1 raw)...done!")
    return bcm_dfs + bpm_dfs, bpm_names


def read_data(filepath: Union[str, Path],
              t_range: Union[tuple[int, int], None] = (-800, 400),
              is_opt: bool = False):
    """ Read and consolidate dataset. If *is_opt* is set, read the *filepath* as the optimized
    dataset, otherwise, as raw formatted.
    """
    logger.info(f"Reading {filepath}...")
    if is_opt:
        # read the converted file, smaller size.
        with pd.HDFStore(filepath, mode="r") as store:
            t0_s = store.get_storer('TimeWindow').attrs.t_zero
            # BCM-FSCALE
            bcm_fscale_map = None
            if '/BCM' in store.keys():
                attrs = store.get_storer('BCM').attrs
                if 'fscale_json' in attrs:
                    bcm_fscale_map = json.loads(attrs.fscale_json)
            df_all = pd.concat([store[k] for k in store.keys()], axis=1)
            if bcm_fscale_map is not None:
                df_all.attrs['BCM-FSCALE'] = bcm_fscale_map
        #
        t0_idx: int = (df_all["t_us"]==0.0).argmax()
        if t_range is not None:
            logger.info(f"Reading {filepath}...done!")
            return df_all.iloc[t0_idx + t_range[0]:t0_idx + t_range[1], :], t0_s
        logger.info(f"Reading {filepath}...done!")
        return df_all, t0_s

    # read with raw
    with pd.HDFStore(filepath, mode="r") as store:
        if '/grp' in store.keys():
            dfs, bpm_names = _process_format_v1(store)
        else:
            dfs, bpm_names = _process_format_v0(store)
        #
    if dfs is None:
        logger.error("Error reading data.")
        return None, ""

    df_all = pd.concat(dfs, axis=1).sort_index(axis=1)

    npermit_names = ('BCM4_NPERMIT', 'BCM5_NPERMIT', 'BCM5_NPERMIT')
    if all(i not in df_all for i in npermit_names):
        logger.error("No NPERMIT signals, cannot figure out T trip.")
        return None, ""

    # find the first index loc (int) that npermit goes high (1)
    # find the first occurence of BCM?_NPERMIT that with high bits, and drop others
    # if none is found, throw out error
    npermit_col: Union[str, None] = None
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
        logger.error("No high bit signals in NPERMITs, cannot figure out T trip.")
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

    # produce DBCM columns if possible
    # look for BCM FSCALE data
    bcm_fscale_map = None
    for i in dfs:
        if 'fscale' in i.attrs:
            bcm_fscale_map = i.attrs['fscale']
            break
    if bcm_fscale_map is not None:
        logger.info(f"Generating DBCM dataset...")
        logger.debug(f"Got BCM FSCALE data: {bcm_fscale_map}")
        _generate_dbcm_inplace(df, bcm_fscale_map)
        # attach the fscale data
        df.attrs['BCM-FSCALE'] = bcm_fscale_map

    logger.info(f"Reading {filepath}...done!")
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


def plot(df: pd.DataFrame, t0: str, title: str, **kws):
    """ Keyword Arguments:
    fig_dpi: int, figsize: tuple
    """

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1,
                                        figsize=kws.get('figsize', (12.4, 8)),
                                        dpi=kws.get('fig_dpi', DEFAULT_MPL_FIG_DPI))

    xylabel_fontdict = {"size": DEFAULT_MPL_FONT_SIZE + 2, "family": DEFAULT_MPL_FONT_FAMILY}
    xyticks_fontdict = {"size": DEFAULT_MPL_FONT_SIZE + 1, "family": DEFAULT_MPL_FONT_FAMILY}
    title_fontdict = {"size": DEFAULT_MPL_FONT_SIZE + 4, "family": DEFAULT_MPL_FONT_FAMILY}
    grid_color = "#7F8C8D"

    # BCM
    bcm_cols = [c for c in df.columns if c.startswith("BCM") and not c.endswith('NPERMIT')]
    if bcm_cols:
        if df[bcm_cols].isna().all().all():
            _plot_no_data(ax1, "All NaN")
        else:
            df.plot(x='t_us', y=bcm_cols, ax=ax1, xlabel="", alpha=0.85)
    else:
        # show NO DATA
        _plot_no_data(ax1)

    ax1.set_ylabel("Current $[\mu A]$")
    ax1.set_title(title, fontsize=title_fontdict['size'],
                  fontfamily=title_fontdict['family'])

    ax1r = ax1.twinx()
    npermit_col = [c for c in df.columns if c.endswith('NPERMIT')][0]
    df.plot(x='t_us', y=npermit_col, c='#2C3E50', ls='-.', lw=1, ax=ax1r,
            label=npermit_col, ylim=(-0.2, 1.2), alpha=0.85)
    ax1r.set_ylabel("NPERMIT")
    ax1r.legend(loc="lower left")
    # make xypos reported by mousemove against ax1, while make ax1r also seen.
    ax1.set_zorder(10)
    ax1.patch.set_visible(False)

    # BPM
    bpm_amp_cols = [c for c in df.columns if 'MAG' in c]
    bpm_pha_cols = [c for c in df.columns if 'PHA' in c]
    if bpm_amp_cols:
        if df[bpm_amp_cols].isna().all().all():
            _plot_no_data(ax2, "All NaN")
        else:
            df.plot(x='t_us', y=bpm_amp_cols, ax=ax2, xlabel="", alpha=0.85)
    else:
        _plot_no_data(ax2)
    if bpm_pha_cols:
        if df[bpm_pha_cols].isna().all().all():
            _plot_no_data(ax3, "All NaN")
        else:
            df.plot(x='t_us', y=bpm_pha_cols, ax=ax3, alpha=0.85)
    else:
        _plot_no_data(ax3)
    ax2.set_ylabel("Magnitude [mVpp]")
    ax3.set_xlabel("Time $[\mu s]$")
    ax3.set_ylabel("$\Phi [^o]$ @ 80.5 MHz")
    ax3.annotate(f"$T_0$ = {t0}", (0, -0.3), xycoords='axes fraction',
                 fontfamily="monospace", fontsize=xylabel_fontdict['size'])

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
    return fig


def _generate_dbcm_inplace(df: pd.DataFrame, bcm_fscale_map: dict) -> None:
    """ Generate and add the DBCM data columns to the original dataframe,
    with the given BCM FSCALE data.
    """
    n1 = "BCM_D1120"
    n2 = "BCM_D2183"
    n3 = "BCM_D2264"
    n4 = "BCM_D2519"
    n5 = "BCM_D2675"
    n6 = "BCM_D3936"
    n7 = "BCM_D4169"
    n8 = "BCM_D5521"
    n9 = "BCM_D5789"
    n1c = "BCM_D1120c"
    # s1 := BCM_D1120, f1 := bcm_fscal_map[...]
    # s2 := BCM_D2183
    # s3 := BCM_D2264
    # s4 := BCM_D2519
    # s5 := BCM_D2675
    # s6 := BCM_D3936
    # s7 := BCM_D4169
    # s8 := BCM_D5521
    # s9 := BCM_D5789
    # s1c := BCM_D1120c, f1c := ...COPY...
    #
    # d1 := DBCM_LS1TRANS (D1120 - D2183) = s1 * f1 - s2 * f2
    # d2 := DBCM_CHRGSTAT (D2183 - D2264) = s2 * f2 - s3 * f3
    # d3 := DBCM_STRPEFF  (D2264 - D2519) = s3 * f3 - s4 * f4
    # d4 := DBCM_LS2TRANS (D2675 - D3936) = s5 * f5 - s6 * f6
    # d5 := DBCM_LS3TRANS (D4169 - D5521) = s7 * f7 - s8 * f8
    # d6 := DBCM_LINACBDS (D1120c - D5521) = s1c *f1c - s8 * f8
    # d7 := DBCM_LINACTGT (D1120c - D5789) = s1c * f1c - s9 * f9
    f1 = bcm_fscale_map[BCM_FSCALE_NAME_MAP[n1]]
    f2 = bcm_fscale_map[BCM_FSCALE_NAME_MAP[n2]]
    f3 = bcm_fscale_map[BCM_FSCALE_NAME_MAP[n3]]
    f4 = bcm_fscale_map[BCM_FSCALE_NAME_MAP[n4]]
    f5 = bcm_fscale_map[BCM_FSCALE_NAME_MAP[n5]]
    f6 = bcm_fscale_map[BCM_FSCALE_NAME_MAP[n6]]
    f7 = bcm_fscale_map[BCM_FSCALE_NAME_MAP[n7]]
    f8 = bcm_fscale_map[BCM_FSCALE_NAME_MAP[n8]]
    f9 = bcm_fscale_map[BCM_FSCALE_NAME_MAP[n9]]
    f1c = bcm_fscale_map[BCM_FSCALE_NAME_MAP[n1c]]

    dfc = df.copy()
    # the scaled waveform
    s1 = dfc.get(n1) * f1 if n1 in dfc else None
    s2 = dfc.get(n2) * f2 if n2 in dfc else None
    s3 = dfc.get(n3) * f3 if n3 in dfc else None
    s4 = dfc.get(n4) * f4 if n4 in dfc else None
    s5 = dfc.get(n5) * f5 if n5 in dfc else None
    s6 = dfc.get(n6) * f6 if n6 in dfc else None
    s7 = dfc.get(n7) * f7 if n7 in dfc else None
    s8 = dfc.get(n8) * f8 if n8 in dfc else None
    s9 = dfc.get(n9) * f9 if n9 in dfc else None
    s1c = dfc.get(n1c) * f1c if n1c in dfc else None

    # dbcm
    if s1 is not None and s2 is not None:
        df['DBCM_LS1TRANS'] = s1 - s2
        logger.debug(f"Added DBCM_LS1TRANS: {n1} - {n2}")
    if s2 is not None and s3 is not None:
        df['DBCM_CHRGSTAT'] = s2 - s3
        logger.debug(f"Added DBCM_CHRGSTAT: {n2} - {n3}")
    if s3 is not None and s4 is not None:
        df['DBCM_STRPEFF'] = s3 - s4
        logger.debug(f"Added DBCM_STRPEFF: {n3} - {n4}")
    if s5 is not None and s6 is not None:
        df['DBCM_LS2TRANS'] = s5 - s6
        logger.debug(f"Added DBCM_LS2TRANS: {n5} - {n6}")
    if s7 is not None and s8 is not None:
        df['DBCM_LS3TRANS'] = s7 - s8
        logger.debug(f"Added DBCM_LS3TRANS: {n7} - {n8}")
    if s1c is not None and s8 is not None:
        df['DBCM_LINACBDS'] = s1c - s8
        logger.debug(f"Added DBCM_LINACBDS: {n1c} - {n8}")
    if s1c is not None and s9 is not None:
        df['DBCM_LINACTGT'] = s1c - s9
        logger.debug(f"Added DBCM_LINACTGT: {n1c} - {n9}")


def _to_fix_bcm_dateset(full_filename: str) -> bool:
    """ Return if the BCM dataframe needs fix.
    """
    # for the datafile created before DATE_PRIOR_FIX, rename the BCM columns:
    # - BCM_D1120 -> BCM_D1120c
    # - BCM_D2183 -> BCM_D0989
    try:
        # get the date from the filename.
        pth_name = Path(full_filename).name
        created_date = datetime.strptime(pth_name[:15], "%Y%m%dT%H%M%S")
    except Exception as e:
        logger.warning(f"Failed get created date from filename {store.filename}.")
        fix_bcm = False
    else:
        fix_bcm = created_date < DATE_PRIOR_FIX
    logger.debug(f"To fix BCM of {full_filename}? {fix_bcm}")
    return fix_bcm


if __name__ == "__main__":

    fault_id = "23635"
    filepath = Path(f"test1/{fault_id}.h5")

    df, t0_str = read_data(filepath)

    fig = plot(df, t0_str, f"MPS fault ID: {fault_id}")
    fig.tight_layout()
    for typ in ("png", "pdf"):
        fig_outpath = filepath.parent.joinpath(f"{fault_id}.{typ}")
        fig.savefig(fig_outpath)
    plt.show()

