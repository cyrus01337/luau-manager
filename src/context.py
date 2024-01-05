from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, Optional, TypedDict

__all__ = ("Context",)


class Payload(TypedDict):
    zipball_url: str
    target_commitish: str
    name: str


# TODO: Prefer tempfile.mkstemp over NamedTemporaryFile for best practice and to
# potentially resolve type error if practical
class Context:
    def __init__(
        self,
        data: dict[str, Any],
        *,
        temp_dir: Optional[TemporaryDirectory] = None,
        temp_zipfile: Optional[NamedTemporaryFile] = None  # type: ignore
    ):
        payload = Payload(**data)
        self.asset_url = payload["zipball_url"]
        self.commit_hash = payload["target_commitish"]
        self.version = float(payload["name"])
        self.temp_dir = temp_dir or TemporaryDirectory()
        self.temp_zipfile = temp_zipfile or NamedTemporaryFile(
            dir=self.temp_dir.name, suffix=".zip"
        )
