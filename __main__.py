"""
TODO: Stop using tempfiles - cache and build versions individually
TODO: Setup version shims
TODO: Type
TODO: Modularise
TODO: Add CLI support
TODO: Setup versioning for tool
TODO: Find out minimum Python version required
TODO: Make easy to install
TODO: Document
"""
# TODO: Only import what's functionally necessary
import dataclasses
import os
import pathlib
import subprocess
import sys
import tempfile
import zipfile
from typing import TypedDict

import requests

DESTINATION_DIR = pathlib.Path("/usr/local/bin")
VERSION_FILE = pathlib.Path.home() / ".luau-version"
BUILD_COMMANDS = {
    "cmake": [
        "cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo",
        "cmake --build . --target Luau.Repl.CLI --config RelWithDebInfo",
        "cmake --build . --target Luau.Analyze.CLI --config RelWithDebInfo",
    ],
    "make": [
        "make config=release luau luau-analyze",
    ],
}
SUCCESS = 0
MAKE = "make"
CMAKE = "cmake"


class Payload(TypedDict):
    zipball_url: str
    target_commitish: str
    name: str


@dataclasses.dataclass
class Context:
    payload: Payload | None


class InitFailed(Exception):
    pass


class BuildFailed(Exception):
    pass


def parse_version(text):
    return float(text)


def maybe_get_version():
    try:
        with VERSION_FILE.open("r") as fh:
            return float(fh.read().strip())
    except FileNotFoundError:
        return None


def set_version(version):
    with VERSION_FILE.open("w") as fh:
        fh.write(str(version))


def request_zipfile_url(ctx: Context):
    LUAU_LATEST_RELEASE = "https://api.github.com/repos/Roblox/luau/releases/latest"
    response = requests.get(LUAU_LATEST_RELEASE)
    payload = response.json()

    if ctx.payload is None:
        ctx.payload = payload

    return payload["zipball_url"]


def download_zipfile(url, *, file):
    response = requests.get(url, stream=True)

    for chunk in response.iter_content(10_000):
        file.write(chunk)


def determine_extracted_subdir(ctx, target_dir):
    commit_hash = ctx.payload["target_commitish"]
    shortened_hash = commit_hash[:7]

    return target_dir / f"luau-lang-luau-{shortened_hash}"


def extract_zipfile(ctx, file, *, target_dir):
    with zipfile.PyZipFile(file) as archive:
        archive.extractall(path=target_dir)

    return determine_extracted_subdir(ctx, target_dir)


def has_cmake():
    spawned_process_exit_code = os.system("which cmake &> /dev/null")

    return spawned_process_exit_code == SUCCESS


def has_make():
    spawned_process_exit_code = os.system("which make &> /dev/null")

    return spawned_process_exit_code == SUCCESS


def get_build_tool() -> str:
    if has_cmake():
        return CMAKE
    elif has_make():
        return MAKE

    raise InitFailed("Missing essential build tools: cmake or make not found.")


def determine_build_dir(build_tool, target_dir: pathlib.Path):
    if build_tool == CMAKE:
        return target_dir / "cmake"
    elif build_tool == MAKE:
        return target_dir

    return target_dir


def build_luau(target_dir: pathlib.Path):
    build_tool = get_build_tool()
    build_dir = determine_build_dir(build_tool, target_dir)
    commands = BUILD_COMMANDS[build_tool]

    build_dir.mkdir(exist_ok=True)

    for command in commands:
        try:
            subprocess.run(command, cwd=build_dir, check=True, shell=True)
        except subprocess.CalledProcessError as error:
            raise BuildFailed(error.output)
        except OSError as error:
            print(f'Failed to run command "{command}":', end="\n\n", file=sys.stderr)

            raise error

    luau_filepath = build_dir / "luau"
    luau_analyze_filepath = build_dir / "luau-analyze"

    return luau_filepath, luau_analyze_filepath


def main():
    ctx = Context(payload=None)
    # TODO: Refactor Context initialisation
    zipfile_url = request_zipfile_url(ctx)
    version = parse_version(ctx.payload["name"]) if ctx.payload else None
    cached_version = maybe_get_version()
    luau_executable = DESTINATION_DIR / "luau"
    luau_analyse = DESTINATION_DIR / "luau-analyze"

    if (
        version
        and cached_version
        and version == cached_version
        and (luau_executable.exists() or luau_analyse.exists())
    ):
        existing_executable = "luau" if luau_executable.exists() else "luau-analyze"

        raise InitFailed(
            f"{existing_executable} already exists with this version ({cached_version})"
        )

    with (
        tempfile.TemporaryDirectory() as temp_dir_path,
        tempfile.NamedTemporaryFile(dir=temp_dir_path, suffix=".zip") as temp_file,
    ):
        temp_dir = pathlib.Path(temp_dir_path)

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
