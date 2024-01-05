# TODO: Stop using tempfiles - cache and build versions individually
import subprocess
from pathlib import Path
from sys import stderr
from tempfile import NamedTemporaryFile, TemporaryDirectory
from zipfile import PyZipFile

import requests

from src import errors, shims

__all__ = ("build",)

DESTINATION_DIR = Path("/usr/local/bin")
MAKE = "make"
CMAKE = "cmake"
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


def _download_zipfile(url, *, file):
    response = requests.get(url, stream=True)

    for chunk in response.iter_content(10_000):
        file.write(chunk)


# TODO: Review
def _determine_extracted_subdir(ctx, target_dir):
    shortened_hash = ctx.commit_hash[:7]

    return target_dir / f"luau-lang-luau-{shortened_hash}"


def _extract_zipfile(ctx, file, *, target_dir):
    with PyZipFile(file) as archive:
        archive.extractall(path=target_dir)

    return _determine_extracted_subdir(ctx, target_dir)


def _run_shell_command(command, *, cwd=Path.cwd()):
    try:
        subprocess.run(command, cwd=cwd, check=True, shell=True)
    except subprocess.CalledProcessError as error:
        raise errors.BuildFailed(error.output) from error
    except OSError as error:
        print(f'Failed to run command "{command}":', end="\n\n", file=stderr)

        raise errors.BuildFailed(str(error)) from error


def _has_cmake():
    try:
        _run_shell_command("which cmake &> /dev/null")
    except errors.BuildFailed:
        return False
    else:
        return True


def _has_make():
    try:
        _run_shell_command("which make &> /dev/null")
    except errors.BuildFailed:
        return False
    else:
        return True


def _get_compile_tool() -> str:
    if _has_cmake():
        return CMAKE
    elif _has_make():
        return MAKE

    raise errors.InitFailed("Missing essential build tools: cmake or make not found.")


def _determine_build_dir(build_tool, target_dir: Path):
    if build_tool == CMAKE:
        return target_dir / "cmake"
    elif build_tool == MAKE:
        return target_dir

    return target_dir


def _compile(target_dir: Path):
    build_tool = _get_compile_tool()
    build_dir = _determine_build_dir(build_tool, target_dir)
    commands = BUILD_COMMANDS[build_tool]

    build_dir.mkdir(exist_ok=True)

    for command in commands:
        _run_shell_command(command, cwd=build_dir)

    return build_dir


def build(ctx):
    cached_version_found = shims.maybe_get_version()
    luau_executable = DESTINATION_DIR / "luau"
    luau_analyse = DESTINATION_DIR / "luau-analyze"

    if (
        cached_version_found
        and ctx.version == cached_version_found
        and (luau_executable.exists() or luau_analyse.exists())
    ):
        existing_executable = "luau" if luau_executable.exists() else "luau-analyze"

        raise errors.InitFailed(
            f"{existing_executable} already exists with this version ({cached_version_found})"
        )

    with (
        TemporaryDirectory() as temp_dir_path,
        NamedTemporaryFile(dir=temp_dir_path, suffix=".zip") as temp_file,
    ):
        temp_dir = Path(temp_dir_path)

        # sourcery skip: extract-method
        _download_zipfile(ctx.asset_url, file=temp_file)
        temp_file.seek(0)

        extracted_subdir = _extract_zipfile(ctx, temp_file, target_dir=temp_dir)
        build_dir = _compile(target_dir=extracted_subdir)

        _run_shell_command(f"sudo cp -f luau* {DESTINATION_DIR}", cwd=build_dir)
        shims.set_version(ctx.version)
