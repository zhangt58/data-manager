""" The raw .h5 files generated before _DATETIME1:
- BPM t0 is the timestamp of the *first* point of waveform: TimeType 0
- BCM t0 is the timestamp of the *last*  point of waveform: TimeType 1
After _DATETIME1:
- BCM t0 will be the timestamp of the *first* point of waveform: TimeType 1
"""
from datetime import datetime

_DATETIME1 = datetime.strptime("2025-02-13", "%Y-%m-%d")
