import subprocess
from pathlib import Path

here = Path(__file__).parent
reader = str(Path(here.parents[1], "esofile-reader"))

process = subprocess.run(f"cd {reader} & poetry build", shell=True)

if process.returncode == 0:
    wheels = [w for w in Path(reader, "dist").iterdir() if w.suffix == ".whl"]

    # pick up only wheel for python 3.8
    wheel = next(filter(lambda x: "38" in x, wheels))

    subprocess.run("pip uninstall -y esofile-reader")
    subprocess.run(f"pip install {wheel}")
