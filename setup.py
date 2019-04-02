
from cx_Freeze import setup, Executable
import sys

# exclude unneeded packages. More could be added. Has to be changed for
# other programs.
build_exe_options = {"excludes": ["tkinter"],
                     "optimize": 2,
                     "includes":["numpy",'numpy.core._methods', 'numpy.lib.format']}

# Information about the program and build command. Has to be adjusted for
# other programs
setup(
    name="MyProgram",                           # Name of the program
    version="0.1",                              # Version number
    description="MyDescription",                # Description
    options = {"build_exe": build_exe_options}, # <-- the missing line
    executables=[Executable('C:/Users/vojte/Desktop/Python/EsoReader/app.py',     # Executable python file
                            base = ("Win32GUI" if sys.platform == "win32"
                            else None))],
)