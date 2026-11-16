"""Write HTTP Archive (HAR) files."""

from __future__ import annotations

import builtins
import json.encoder
from datetime import datetime
from os import PathLike
from types import TracebackType
from typing import IO, Any, Callable

from ._models import (
    Browser,
    Cache,
    CacheEntry,
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
    "CacheEntry",
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


def _make_encode() -> Callable[[Any], str]:
    encoder = json.JSONEncoder(allow_nan=False)
    try:
        # Built once; `JSONEncoder.encode` rebuilds it on every call. PyPy has none.
        c_encode = json.encoder.c_make_encoder(  # type: ignore[attr-defined]
            None, encoder.default, json.encoder.encode_basestring_ascii, None, ": ", ", ", False, False, False
        )
    except (AttributeError, TypeError):
        return encoder.encode
    return lambda o: "".join(c_encode(o, 0))


_encode = _make_encode()


class HarFile:
    _fd: IO[str]
    _creator: Creator
    _browser: Browser
    _comment: str | None
    _is_first_entry: bool = True
    _has_preamble: bool = False
    _is_managed_fd: bool = False
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
        name_or_fd: str | PathLike[str] | IO[str],
        *,
        creator: Creator | None = None,
        browser: Browser | None = None,
        comment: str | None = None,
    ) -> HarFile:
        """Open a HAR file for writing."""
        fd: IO[str]
        if isinstance(name_or_fd, (str, PathLike)):
            fd = builtins.open(name_or_fd, "w")
            is_managed = True
        else:
            fd = name_or_fd
            is_managed = False
        instance = cls(fd=fd, creator=creator, browser=browser, comment=comment)
        instance._is_managed_fd = is_managed
        return instance

    def close(self) -> None:
        """Close the HAR file."""
        if self.closed:
            return None
        self.closed = True
        if not self._has_preamble:
            self._write_preamble()
            self._has_preamble = True
        self._write_postscript()
        if self._is_managed_fd:
            self._fd.close()

    def flush(self) -> None:
        self._fd.flush()

    def __enter__(self) -> HarFile:
        return self

    def __exit__(
        self,
        type: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if type is None or self._has_preamble:
            self.close()
        elif self._is_managed_fd:
            self._fd.close()
        self.closed = True
        return None

    def add_entry(
        self,
        *,
        startedDateTime: datetime | str,
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
        if self.closed:
            raise ValueError("I/O operation on closed file.")
        if not self._has_preamble:
            self._write_preamble()
            self._has_preamble = True
        separator = "\n" if self._is_first_entry else ",\n"
        dumps = _encode
        # ISO 8601 output never needs escaping, so only user-supplied strings go through the encoder.
        if isinstance(startedDateTime, datetime):
            if startedDateTime.tzinfo is None:
                startedDateTime = startedDateTime.astimezone()
            started_date_time = f'"{startedDateTime.isoformat()}"'
        else:
            started_date_time = dumps(startedDateTime)
        # The common case is no cache info; avoid allocating a Cache and
        # encoding an empty dict (``dumps(Cache().asdict())`` is just ``"{}"``).
        cache_json = "{}" if cache is None else dumps(cache.asdict())
        chunk = (
            f"{separator}            {{"
            f'\n                "startedDateTime": {started_date_time},'
            f'\n                "time": {dumps(time)},'
            f'\n                "request": {dumps(request.asdict())},'
            f'\n                "response": {dumps(response.asdict())},'
            f'\n                "timings": {dumps(timings.asdict())},'
            f'\n                "cache": {cache_json}'
        )
        if serverIPAddress:
            chunk += f',\n                "serverIPAddress": {dumps(serverIPAddress)}'
        if connection:
            chunk += f',\n                "connection": {dumps(connection)}'
        if comment:
            chunk += f',\n                "comment": {dumps(comment)}'
        chunk += "\n            }"
        self._fd.write(chunk)
        self._is_first_entry = False

    def _write_preamble(self) -> None:
        creator = f"""{{
            "name": {_encode(self._creator.name)},
            "version": {_encode(self._creator.version)}"""
        if self._creator.comment:
            creator += f',\n            "comment": {_encode(self._creator.comment)}'
        creator += "\n        }"
        browser = f"""{{
            "name": {_encode(self._browser.name)},
            "version": {_encode(self._browser.version)}"""
        if self._browser.comment:
            browser += f',\n            "comment": {_encode(self._browser.comment)}'
        browser += "\n        }"
        self._fd.write(f"""{{
    "log": {{
        "version": "{HAR_VERSION}",
        "creator": {creator},
        "browser": {browser}""")
        if self._comment:
            self._fd.write(f',\n        "comment": {_encode(self._comment)}')
        self._fd.write(',\n        "entries": [')

    def _write_postscript(self) -> None:
        if self._is_first_entry:
            self._fd.write("]\n    }\n}")
        else:
            self._fd.write("\n        ]\n    }\n}")


open = HarFile.open
