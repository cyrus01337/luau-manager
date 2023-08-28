"""
TODO: Track Luau versions
TODO: Replace exits with actual values
TODO: Make sure prerequisites are installed before building
TODO: Stop using tempfiles - cache and build versions individually
TODO: Include a way to avoid downloads if current version is identical to latest release
TODO: Type
TODO: Make easy to install
TODO: Document
"""
import dataclasses
import os
import subprocess
import sys
import tempfile
import zipfile

import requests


@dataclasses.dataclass
class Context:
    payload: dict | None


def request_zipfile_url(ctx):
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

    return os.path.join(target_dir, f"Roblox-luau-{shortened_hash}")


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

    luau_filepath = os.path.join(cmake_dir, "luau")
    luau_analyze_filepath = os.path.join(cmake_dir, "luau-analyze")

    return luau_filepath, luau_analyze_filepath


def main():
    DESTINATION_DIR = "/usr/local/bin"
    ctx = Context(payload=None)
    zipfile_url = request_zipfile_url(ctx)

    with (
        tempfile.TemporaryDirectory() as temp_dir,
        tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".zip") as temp_file,
    ):
        download_zipfile(zipfile_url, file=temp_file)
        temp_file.seek(0)

        extracted_subdir = extract_zipfile(ctx, temp_file, target_dir=temp_dir)
        luau_filepath, luau_analyze_filepath = build_luau(target_dir=extracted_subdir)

        os.system(f"sudo cp -f {luau_filepath} {DESTINATION_DIR}")
        os.system(f"sudo cp -f {luau_analyze_filepath} {DESTINATION_DIR}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Cancelling...")
