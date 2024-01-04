"""
TODO: Replace exits with actual values
TODO: Make sure prerequisites are installed before building
TODO: Stop using tempfiles - cache and build versions individually
TODO: Setup version shims
TODO: Type
TODO: Add CLI support
TODO: Setup versioning for tool
TODO: Find out minimum Python version required
TODO: Make easy to install
TODO: Document
"""
# TODO: Only import what's functionally necessary
import dataclasses
import os
import subprocess
import sys
import tempfile
import zipfile
from typing import TypedDict

import requests

DESTINATION_DIR = "/usr/local/bin"
VERSION_FILEPATH = os.path.join(os.path.expanduser("~"), ".luau-version")


class Payload(TypedDict):
    zipball_url: str
    target_commitish: str
    name: str


@dataclasses.dataclass
class Context:
    payload: Payload | None


def parse_version(text):
    return float(text)


def maybe_get_version():
    try:
        with open(VERSION_FILEPATH, "r") as fh:
            return float(fh.read().strip())
    except FileNotFoundError:
        return None


def set_version(version):
    with open(VERSION_FILEPATH, "w") as fh:
        fh.write(str(version))


def request_zipfile_url(ctx: Context):
    LUAU_LATEST_RELEASE = "https://api.github.com/repos/Roblox/luau/releases/latest"
    response = requests.get(LUAU_LATEST_RELEASE)

    # TODO: Handle error appropriately
    if not response.ok:
        exit(os.EX_UNAVAILABLE)

    payload = response.json()

    if ctx.payload is None:
        ctx.payload = payload

    return payload["zipball_url"]


def download_zipfile(url, *, file):
    response = requests.get(url, stream=True)

    # TODO: Handle error appropriately
    if not response.ok:
        exit(os.EX_UNAVAILABLE)

    for chunk in response.iter_content(10_000):
        file.write(chunk)


def determine_extracted_subdir(ctx, target_dir):
    commit_hash = ctx.payload["target_commitish"]
    shortened_hash = commit_hash[:7]

    return os.path.join(target_dir, f"luau-lang-luau-{shortened_hash}")


def extract_zipfile(ctx, file, *, target_dir):
    with zipfile.PyZipFile(file) as archive:
        archive.extractall(path=target_dir)

    return determine_extracted_subdir(ctx, target_dir)


# TODO: Default to CMake, use Make as fallback
def build_luau(target_dir):
    SUCCESS = 0
    cmake_dir = os.path.join(target_dir, "cmake")
    commands = (
        "cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo",
        "cmake --build . --target Luau.Repl.CLI --config RelWithDebInfo",
        "cmake --build . --target Luau.Analyze.CLI --config RelWithDebInfo",
    )

    os.mkdir(cmake_dir)

    for command in commands:
        try:
            result = subprocess.run(command, cwd=cmake_dir, shell=True)

            # TODO: Handle error appropriately
            if result.returncode < SUCCESS:
                exit(os.EX_UNAVAILABLE)
        except Exception as error:
            print(f'Failed to run command "{command}":', end="\n\n", file=sys.stderr)

            raise error

    # TODO: Acknowledge additional files
    luau_filepath = os.path.join(cmake_dir, "luau")
    luau_analyze_filepath = os.path.join(cmake_dir, "luau-analyze")

    return luau_filepath, luau_analyze_filepath


def main():
    ctx = Context(payload=None)
    # TODO: Refactor Context initialisation
    zipfile_url = request_zipfile_url(ctx)
    version = parse_version(ctx.payload["name"]) if ctx.payload else None
    cached_version = maybe_get_version()
    luau_executable_exists = os.path.isfile(os.path.join(DESTINATION_DIR, "luau"))

    if (
        version
        and cached_version
        and version == cached_version
        and luau_executable_exists
    ):
        raise ValueError(f"Luau already exists with this version ({cached_version})")

    with (
        tempfile.TemporaryDirectory() as temp_dir,
        tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".zip") as temp_file,
    ):
        # sourcery skip: extract-method
        download_zipfile(zipfile_url, file=temp_file)
        temp_file.seek(0)

        extracted_subdir = extract_zipfile(ctx, temp_file, target_dir=temp_dir)
        luau_filepath, luau_analyze_filepath = build_luau(target_dir=extracted_subdir)

        # TODO: Refactor
        os.system(f"sudo cp -f {luau_filepath} {DESTINATION_DIR}")
        os.system(f"sudo cp -f {luau_analyze_filepath} {DESTINATION_DIR}")
        set_version(version)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Cancelling...")
