from pathlib import Path
import subprocess

here = Path(__file__).parent
reader = str(Path(here.parents[1], "esofile-reader"))

process = subprocess.run(f"cd {reader} & python setup.py bdist_wheel", shell=True)

if process.returncode == 0:
    wheel = [w for w in Path(reader, "dist").iterdir() if w.suffix == ".whl"][0]
    subprocess.run(f"pip uninstall -y esofile-reader")
    subprocess.run(f"pip install {wheel}")

