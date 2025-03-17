set PY_EXE="C:\Users\zhangt\AppData\Local\Programs\Python\Python311\python.exe"
:: %PY_EXE% -m pip install wheel
%PY_EXE% setup.py bdist_wheel
%PY_EXE% -m pip uninstall -y dm.wfdata
%PY_EXE% -m pip install --find-links=.\dist dm.wfdata --upgrade