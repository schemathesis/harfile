"""Write HTTP Archive (HAR) files."""

from __future__ import annotations

import builtins
import json
from dataclasses import asdict
from datetime import datetime
from os import PathLike
from types import TracebackType
from typing import IO, Any

from ._models import (
    Browser,
    Cache,
    Content,
    Cookie,
    Creator,
    PostData,
    PostParameter,
    Record,
    Request,
    Response,
    Timings,
)
from ._version import VERSION

__all__ = [
    "open",
    "HarFile",
    "Browser",
    "Creator",
    "Cache",
    "Request",
    "Response",
    "Timings",
    "Cookie",
    "Record",
    "PostData",
    "PostParameter",
    "Content",
    "HAR_VERSION",
]

HAR_VERSION = "1.2"


class HarFile:
    _fd: IO[str]
    _creator: Creator
    _browser: Browser
    _comment: str | None
    _is_first_entry: bool = True
    _has_preable: bool = False
    closed: bool = False

    def __init__(
        self,
        fd: IO[str],
        *,
        creator: Creator | None = None,
        browser: Browser | None = None,
        comment: str | None = None,
    ):
        self._fd = fd
        self._creator = creator or Creator(name="harfile", version=VERSION)
        self._browser = browser or Browser(name="", version="")
        self._comment = comment

    @classmethod
    def open(
        cls,
        name_or_fd: str | PathLike | IO[str],
        *,
        creator: Creator | None = None,
        browser: Browser | None = None,
        comment: str | None = None,
    ) -> HarFile:
        """Open a HAR file for writing."""
        fd: IO[str]
        if isinstance(name_or_fd, (str, PathLike)):
            fd = builtins.open(name_or_fd, "w")
        else:
            fd = name_or_fd
        return cls(fd=fd, creator=creator, browser=browser, comment=comment)

    def close(self) -> None:
        """Close the HAR file."""
        if self.closed:
            return None
        self.closed = True
        if not self._has_preable:
            self._write_preamble()
            self._has_preable = True
        self._write_postscript()

    def __enter__(self) -> HarFile:
        return self

    def __exit__(
        self,
        type: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if type is None:
            self.close()
        return None

    def add_entry(
        self,
        *,
        startedDateTime: datetime,
        time: int | float,
        request: Request,
        response: Response,
        timings: Timings,
        cache: Cache | None = None,
        serverIPAddress: str | None = None,
        connection: str | None = None,
        comment: str | None = None,
    ) -> None:
        """Add an HTTP request to the HAR file."""
        if not self._has_preable:
            self._write_preamble()
            self._has_preable = True
        self._write_entry(
            startedDateTime=startedDateTime,
            time=time,
            request=request,
            response=response,
            cache=cache,
            timings=timings,
            serverIPAddress=serverIPAddress,
            connection=connection,
            comment=comment,
        )

    def _write_entry(
        self,
        *,
        startedDateTime: datetime,
        time: int | float,
        request: Request,
        response: Response,
        timings: Timings,
        cache: Cache | None = None,
        serverIPAddress: str | None = None,
        connection: str | None = None,
        comment: str | None = None,
    ) -> None:
        separator = "\n" if self._is_first_entry else ",\n"
        self._is_first_entry = False
        self._fd.write(f"{separator}            {{")
        self._fd.write(f'\n                "startedDateTime": "{startedDateTime.isoformat()}",')
        self._fd.write(f'\n                "time": {time},')
        self._fd.write(f'\n                "request": {json.dumps(asdict(request, dict_factory=_dict_factory))},')
        self._fd.write(f'\n                "response": {json.dumps(asdict(response, dict_factory=_dict_factory))},')
        self._fd.write(f'\n                "timings": {json.dumps(asdict(timings, dict_factory=_dict_factory))}')
        if cache:
            self._fd.write(f',\n                "cache": {json.dumps(asdict(cache, dict_factory=_dict_factory))}')
        if serverIPAddress:
            self._fd.write(f',\n                "serverIPAddress": {json.dumps(serverIPAddress)}')
        if connection:
            self._fd.write(f',\n                "connection": {json.dumps(connection)}')
        if comment:
            self._fd.write(f',\n                "comment": {json.dumps(comment)}')
        self._fd.write("\n            }")

    def _write_preamble(self) -> None:
        creator = f"""{{
            "name": "{self._creator.name}",
            "version": "{self._creator.version}\""""
        if self._creator.comment:
            creator += f',\n            "comment": "{self._creator.comment}"'
        creator += "\n        }"
        browser = f"""{{
            "name": "{self._browser.name}",
            "version": "{self._browser.version}\""""
        if self._browser.comment:
            browser += f',\n            "comment": "{self._browser.comment}"'
        browser += "\n        }"
        self._fd.write(f"""{{
    "log": {{
        "version": "{HAR_VERSION}",
        "creator": {creator},
        "browser": {browser}""")
        if self._comment:
            self._fd.write(f'    "comment": "{self._comment}"')
        self._fd.write(',\n        "entries": [')

    def _write_postscript(self) -> None:
        if self._is_first_entry:
            self._fd.write("]\n    }\n}")
        else:
            self._fd.write("\n        ]\n    }\n}")


def _dict_factory(value: list[tuple[str, Any]]) -> dict[str, Any]:
    return {key: value for key, value in value if value is not None}


open = HarFile.open
