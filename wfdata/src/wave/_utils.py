#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Merge the BCM/BPM waveform data from the different HDF5 files (.h5) with the same MPS fault
ID into one HDF5 file.
"""

import re
import pandas as pd

from datetime import datetime
from pathlib import Path
from typing import Literal, Union

from ._log import logger
from ._misc import _DATETIME1


_PATTERN = re.compile(r"(.*)-(.*)-(.*)_(.*)\.h5")
_PATTERN_NO_FTID= re.compile(r"(.*)-(.*)-(.*)\.h5")

# time offset in microseconds, i.e.: t = t + t_offset
T_US_OFFSET = {
    'BCM4': 0,
    'BCM5': 0,
    'BCM6': 0, # -6394,
}


def read_path(dir_path: Path, file_type: str = "h5",
              allow_no_fault_id: bool = False,
              fault_id: int = 90000) -> pd.DataFrame:
    """ Read the file paths of the .h5 files under *dir_path*, combine all into a table, with
    MPS fault ID as the index.
    """
    if isinstance(dir_path, str):
        dir_path = Path(dir_path)
    #
    records = []
    cnt = 0
    for pth in dir_path.rglob(f"*.{file_type}"):
        if not pth.is_file():
            continue
        #
        r = _PATTERN.match(pth.name)
        if r is None and allow_no_fault_id:
            r = _PATTERN_NO_FTID.match(pth.name)
            ftid = fault_id
        if r is None:
            logger.warning(f"Skip {pth}: missing MPS fault ID")
            continue
        if not allow_no_fault_id:
            grp_name, ts1, ts2, ftid = r.groups()
        else:
            grp_name, ts1, ts2 = r.groups()
        ts2 = int(ts2)
        # apply time offset
        ts2 += T_US_OFFSET.get(grp_name, 0)
        ts = datetime.strptime(f"{ts1}.{ts2}", "%Y%m%dT%H%M%S.%f")
        # 0: start, 1: end
        if ts <= _DATETIME1:
            time_type, dev_type = (1, "BCM") if grp_name.startswith('BCM') else (0, "BPM")
        else:
            time_type, dev_type = (0, "BCM") if grp_name.startswith('BCM') else (0, "BPM")
        records.append((ftid, grp_name, pth.name, ts.timestamp(), time_type, dev_type, pth))
        cnt += 1
        logger.debug(f"[{cnt:3d}] Processed {pth}")

    df = pd.DataFrame.from_records(
            records,
            columns=["ID", "Name", "Filename", "TimeStamp", "TimeType", "DevType", "FilePath"])
    df['Date'] = pd.to_datetime(df['TimeStamp'], unit='s').map(
            lambda i: i.strftime("%Y-%m-%d"))
    df['Time'] = pd.to_datetime(df['TimeStamp'], unit='s').map(
        lambda i: i.strftime("%H:%M:%S.%f"))

    return df.set_index('ID').sort_index()


def group_datafiles(ftid: int, df_grp: pd.DataFrame,
                    root_dir: str = ".", overwrite: bool = False) -> Union[Path, None]:
    """ Group rows of datafiles into one, if skip, return None.
    """
    out_filepath = Path(root_dir).joinpath(f"{ftid}.h5")

    if out_filepath.is_file():
        if overwrite:
            logger.info(f"Overwriting {out_filepath}...")
        else:
            logger.debug(f"Skip existing {out_filepath}, force with --overwrite")
            return None

    out_filepath.parent.mkdir(parents=True, exist_ok=True)
    #
    store = pd.HDFStore(out_filepath,
                        mode="w", complevel=9, complib="bzip2")
    _info = {
        "Time": {},
        "Alias": {},
    }
    _dfs = {
        "BCM": [],
        "BPM": []
    }
    for i, row in df_grp.iterrows():
        name, filepath, ts = row.Name, row.FilePath, datetime.fromtimestamp(row.TimeStamp)
        _df = pd.read_hdf(filepath)
        # trim the "<SYS>_<SUBS>:" for BPM names
        _df.index = _df.index.str.replace(r".*:(BPM_D[0-9]{4}.*)", r"\1", regex=True)
        _info['Alias'].update(_df.pop('PV').to_dict())
        if row.DevType == "BPM":
            name = f"BPM_{name}"
        _info['Time'].update({name: ts.isoformat()})
        if row.TimeType == 0:
            _t_idx = pd.date_range(start=ts, periods=_df.shape[1], freq='us')
        else:
            _t_idx = pd.date_range(end=ts, periods=_df.shape[1], freq='us')
        _dfs[row.DevType].append(_df.T.set_index(_t_idx))
    store.put('INFO/PV',
        pd.DataFrame.from_records(
            list(sorted(_info['Alias'].items())),
            columns=['Name', 'PV']).set_index('Name')
    )
    store.put('INFO/TIME',
        pd.DataFrame.from_records(
            list(sorted(_info['Time'].items())),
            columns=['Name', 'Time']).set_index('Name')
    )
    for k, v in _dfs.items():
        if not v:
            continue
        if k == "BPM":
            _df_bpm = pd.concat(v, axis=1)
            _df_bpm_mag = _df_bpm[sorted(c for c in _df_bpm.columns if 'MAG' in c)]
            _df_bpm_pha = _df_bpm[sorted(c for c in _df_bpm.columns if 'PHA' in c)]
            _df_bpm_beamst = _df_bpm[sorted(c for c in _df_bpm.columns if 'BEAMST' in c)]
            store.put("BPM/MAG", _df_bpm_mag)
            store.put("BPM/PHA", _df_bpm_pha)
            store.put("BPM/BEAMST", _df_bpm_beamst)
        elif k == "BCM":
            _df_bcm = pd.concat(v, axis=1)
            _df_bcm_data = _df_bcm[sorted(c for c in _df_bcm.columns if 'NPERMIT' not in c)]
            _df_bcm_npermit = _df_bcm[sorted(c for c in _df_bcm.columns if 'NPERMIT' in c)]
            store.put("BCM/DATA", _df_bcm_data)
            store.put("BCM/NPERMIT", _df_bcm_npermit)
    store.close()
    return out_filepath
