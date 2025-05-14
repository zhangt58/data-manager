#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The cached beam energy at ID 33355 is 177.40 MeV/u
- it is not with the opt or raw data file
- it is in the trip reason details file
  - look upon the MPS fault table shown in the DM-Wave main UI
- assume it's known when pressing Plot buttons
  - I'll bring up this information with Plot Raw/Opt button.

The phase offset data per each BPM:
- it is good to maintain in a CSV file.
- I'll integrate it as one of the data file dependencies, support future adjustment.
"""


import pandas as pd


def read_opt(filepath: str):
    with pd.HDFStore(filepath) as store:
        df_bpm_pha = store['BPM_PHA']
        df_bpm_mag = store['BPM_MAG']
    return pd.concat([df_bpm_pha, df_bpm_mag], axis=1)


df_bpm = read_opt("20250514T033510_33355_opt.h5")
"""
                            BPM_D2212-PHA  BPM_D2223-PHA  ...  BPM_D2313-MAG  BPM_D2466-MAG
2025-05-14 03:35:10.194268      77.895871      16.319468  ...      63.892339     135.222834
2025-05-14 03:35:10.194269      78.019138      15.080133  ...      69.045583     146.068477
2025-05-14 03:35:10.194270      79.754097      15.229056  ...      74.252111     146.696512
2025-05-14 03:35:10.194271      79.614928      17.330705  ...      66.364320     131.713047
2025-05-14 03:35:10.194272      77.324570      17.004350  ...      63.391594     136.043731
...                                   ...            ...  ...            ...            ...
"""
### Energy column calculation ...
