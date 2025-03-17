set PY_EXE="C:\Users\zhangt\AppData\Local\Programs\Python\Python311\python.exe"
%PY_EXE% -m pip install -r requirements.txt
set PY_INSTALLER="C:\Users\zhangt\AppData\Local\Programs\Python\Python311\Scripts\pyinstaller.exe"

%PY_INSTALLER% dm-wave.py --hidden-import='PIL._tkinter_finder' ^
    --exclude-module scipy ^
    --noconfirm --clean --icon .\icons\icon.ico