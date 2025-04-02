@echo off
setlocal

:: dm-wave
set DM_WAVE_CMD="dm-wave.exe"
set WFDATA_DIR="I:\analysis\linac-data\wfdata"

%DM_WAVE_CMD% view %WFDATA_DIR%\raw\MPS-faults.csv ^
    %WFDATA_DIR%\final\images ^
    --trip-info-file %WFDATA_DIR%\raw\trip-info.h5 ^
    --event-filter-file %WFDATA_DIR%\raw\type-filters.txt ^
    --data-dir %WFDATA_DIR%\final\opt ^
    --data-dir %WFDATA_DIR%\final\merged ^
    --data-dir %WFDATA_DIR%\raw\raw ^
    --geometry 1600x900 --theme arc ^
    --fig-dpi 72 --column-widths "{\"Fault_ID\":80,\"Time\":180,\"Power\":75,\"Destination\":200,\"Ion\":60,\"Type\":70,\"Description\":100,\"Devices\":120,\"T Window\":100,\"Threshold\":100}"
