import requests

from src import Context

__all__ = ("init",)

LUAU_LATEST_RELEASE = "https://api.github.com/repos/Roblox/luau/releases/latest"


def init():
    response = requests.get(LUAU_LATEST_RELEASE)
    payload = response.json()

    return Context(payload)
