@echo off
setlocal

:: dm-wave
set DM_WAVE_CMD="C:\Users\zhangt\AppData\Local\Programs\Python\Python311\Scripts\dm-wave.exe"
set WFDATA_DIR="I:\analysis\linac-data\wfdata"

%DM_WAVE_CMD% view %WFDATA_DIR%\raw\MPS-faults.csv ^
    %WFDATA_DIR%\final\images ^
    --trip-info-file %WFDATA_DIR%\raw\trip-info.h5 ^
    --data-dir %WFDATA_DIR%\final\opt ^
    --data-dir %WFDATA_DIR%\final\merged ^
    --data-dir %WFDATA_DIR%\raw\raw ^
    --log-level DEBUG ^
    --geometry 1600x900 --theme adapta ^
    --fig-dpi 72 --column-widths "{\"Fault_ID\":80,\"Time\":200,\"Power\":80,\"Destination\":200,\"Ion\":80,\"Type\":80,\"Description\":100,\"Devices\":120,\"T Window\":100,\"Threshold\":100}"
