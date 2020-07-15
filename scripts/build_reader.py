import re
import subprocess
from pathlib import Path

import semver

reader = str(Path(Path(__file__).parent.parents[1], "esofile-reader"))
PY = "38"

process = subprocess.run(f"cd {reader} & poetry build", shell=True)

if process.returncode == 0:
    wheels = [w for w in Path(reader, "dist").iterdir() if w.suffix == ".whl"]
    p = re.compile(r"^.*?(\d+[.]\d+[.]\d+).*$")
    pairs = []
    for w in wheels:
        if "cp" + PY in str(w):
            v = p.match(str(w)).group(1)
            pairs.append((semver.VersionInfo.parse(v), w))
    print(pairs)
    pairs.sort(key=lambda x: x[0], reverse=True)
    wheel = pairs[0][1]
    subprocess.run("pip uninstall -y esofile-reader")
    subprocess.run(f"pip install {wheel}")
