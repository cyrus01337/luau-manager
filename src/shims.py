# TODO: Setup version shims and shimming
from pathlib import Path

VERSION_FILE = Path.home() / ".luau-version"


# TODO: Retrieve version file from current directory, work upwards until version
# is found or fallback to global version or None
def maybe_get_version():
    try:
        with VERSION_FILE.open("r") as fh:
            return float(fh.read().strip())
    except FileNotFoundError:
        return None


def set_version(version):
    with VERSION_FILE.open("w") as fh:
        fh.write(str(version))
