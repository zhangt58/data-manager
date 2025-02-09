#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from datetime import datetime
from functools import partial
import cothread
from cothread.catools import camonitor, caget
from _init import data_rootdir, logger


data_dir = data_rootdir.joinpath("BCM")

t_delay = 3

# DBCM stripper cs
bcm_D2183 = "DIAG_MTCA06:BCM4:CIRC1MHZ_BCM1_RD"
bcm4_npermit = "DIAG_MTCA06:BCM4:CIRC1MHZ_NPERMIT_RD"
bcm4_t0 = "DIAG_MTCA06:BCM4:CIRC1MHZ_T0_RD"
bcm4_pvnames = [bcm_D2183, bcm4_npermit]
bcm4_index = ["BCM_D2183", "BCM4_NPERMIT"]

# DBCM stripper eff
bcm_D2264 = "DIAG_MTCA06:BCM5:CIRC1MHZ_BCM1_RD"
bcm_D2519 = "DIAG_MTCA06:BCM5:CIRC1MHZ_BCM3_RD"
bcm5_npermit = "DIAG_MTCA06:BCM5:CIRC1MHZ_NPERMIT_RD"
bcm5_t0 = "DIAG_MTCA06:BCM5:CIRC1MHZ_T0_RD"
bcm5_pvnames = [bcm_D2264, bcm_D2519, bcm5_npermit]
bcm5_index = ["BCM_D2264", "BCM_D2519", "BCM5_NPERMIT"]

# DBCM linac to target:
bcm_D1120 = "DIAG_MTCA06:BCM6:CIRC1MHZ_BCM6_RD"
bcm_D5521 = "DIAG_MTCA06:BCM6:CIRC1MHZ_BCM4_RD"
bcm6_npermit = "DIAG_MTCA06:BCM6:CIRC1MHZ_NPERMIT_RD"
bcm6_t0 = "DIAG_MTCA06:BCM6:CIRC1MHZ_T0_RD"
bcm6_pvnames = [bcm_D1120, bcm_D5521, bcm6_npermit]
bcm6_index = ["BCM_D1120", "BCM_D5521", "BCM6_NPERMIT"]

pv_fault_id = "ACS_DIAG:MPS_FIND:FAULT_ID_RD"


def on_fetch(mod_name, pv_names, index, value):
    logger.info(
        f"To fetch {mod_name} waveform in {t_delay}s ... {value}")
    ts = datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
    def f():
        logger.debug(f"Waiting ... ({t_delay}s)")
        cothread.Sleep(t_delay)
        logger.debug(f"Waiting ... done")
        *wf_data, ftid = caget(pv_names + [pv_fault_id])
        subdir = ts.strftime("%Y%m%dT%H%M")
        fn = f"{mod_name}-{ts.strftime('%Y%m%dT%H%M%S-%f')}_{ftid}.h5"
        outpath = data_dir.joinpath(subdir, fn)
        outpath.parent.mkdir(exist_ok=True, parents=True)
        df = pd.DataFrame.from_records(wf_data, index=index)
        df['PV'] = pv_names
        df.to_hdf(outpath, key="data", complevel=9, complib='bzip2')
        logger.info(f"Saved data to {fn}")
    cothread.Spawn(f)

camonitor(bcm4_t0, partial(on_fetch, "BCM4", bcm4_pvnames, bcm4_index))
camonitor(bcm5_t0, partial(on_fetch, "BCM5", bcm5_pvnames, bcm5_index))
camonitor(bcm6_t0, partial(on_fetch, "BCM6", bcm6_pvnames, bcm6_index))

cothread.WaitForQuit()
