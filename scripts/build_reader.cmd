cd ..\..
SET root=%CD%

cd esofile-reader\scripts
build.bat &&^
cd %root%\chartify && .\venv\scripts\activate && .\venv\scripts\pip uninstall -y esofile-reader &&^
.\venv\scripts\pip install %root%\esofile-reader\dist\esofile_reader-0.1.0-cp36-cp36m-win_amd64.whl &&^
.\venv\scripts\deactivate




