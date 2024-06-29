import datetime
import io
import json
import sys

import jsonschema
import pytest
from hypothesis import HealthCheck, Phase, given, settings
from hypothesis import strategies as st

import harfile

# Derived from http://www.softwareishard.com/har/viewer/
DATETIME_PATTERN = r"^(\d{4})(-)?(\d\d)(-)?(\d\d)(T)?(\d\d)(:)?(\d\d)(:)?(\d\d)(\.\d+)?(Z|([+-])(\d\d)(:)?(\d\d))"
RECORD_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "value": {"type": "string"},
        "comment": {"type": "string"},
    },
    "required": ["name", "value"],
    "additionalProperties": False,
}
COOKIE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "value": {"type": "string"},
        "path": {"type": "string"},
        "domain": {"type": "string"},
        "expires": {"type": "string"},
        "httpOnly": {"type": "boolean"},
        "secure": {"type": "boolean"},
        "comment": {"type": "string"},
    },
    "required": ["name", "value"],
    "additionalProperties": False,
}
CACHE_ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "expires": {"type": "string"},
        "lastAccess": {"type": "string"},
        "eTag": {"type": "string"},
        "hitCount": {"type": "integer"},
        "comment": {"type": "string"},
    },
    "required": ["lastAccess", "eTag", "hitCount"],
    "additionalProperties": False,
}
HAR_SCHEMA = {
    "type": "object",
    "properties": {
        "log": {
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "creator": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "comment": {"type": "string"},
                    },
                    "required": ["name", "version"],
                    "additionalProperties": False,
                },
                "browser": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "comment": {"type": "string"},
                    },
                    "required": ["name", "version"],
                    "additionalProperties": False,
                },
                "pages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "startedDateTime": {
                                "type": "string",
                                "format": "date-time",
                                "pattern": DATETIME_PATTERN,
                            },
                            # NOTE: The original schema requires unique `id`, but JSON Schema does not support
                            # uniqueness based on a property value.
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "pageTimings": {
                                "type": "object",
                                "properties": {
                                    "onContentLoad": {"type": "number"},
                                    "onLoad": {"type": "number"},
                                    "comment": {"type": "string"},
                                },
                                "additionalProperties": False,
                            },
                            "comment": {"type": "string"},
                        },
                        "required": ["startedDateTime", "id", "title", "pageTimings"],
                        "additionalProperties": False,
                    },
                },
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pageref": {"type": "string"},
                            "startedDateTime": {
                                "type": "string",
                                "format": "date-time",
                                "pattern": DATETIME_PATTERN,
                            },
                            "time": {"type": "number"},
                            "request": {
                                "type": "object",
                                "properties": {
                                    "method": {"type": "string"},
                                    "url": {"type": "string"},
                                    "httpVersion": {"type": "string"},
                                    "cookies": {
                                        "type": "array",
                                        "items": COOKIE_SCHEMA,
                                    },
                                    "headers": {
                                        "type": "array",
                                        "items": RECORD_SCHEMA,
                                    },
                                    "queryString": {
                                        "type": "array",
                                        "items": RECORD_SCHEMA,
                                    },
                                    "postData": {
                                        "type": "object",
                                        "properties": {
                                            "mimeType": {"type": "string"},
                                            "text": {"type": "string"},
                                            "params": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "value": {"type": "string"},
                                                        "fileName": {"type": "string"},
                                                        "contentType": {"type": "string"},
                                                        "comment": {"type": "string"},
                                                    },
                                                    "required": ["name"],
                                                    "additionalProperties": False,
                                                },
                                            },
                                            "comment": {"type": "string"},
                                        },
                                        "required": ["mimeType"],
                                        "additionalProperties": False,
                                    },
                                    "headersSize": {"type": "integer"},
                                    "bodySize": {"type": "integer"},
                                    "comment": {"type": "string"},
                                },
                                "required": [
                                    "method",
                                    "url",
                                    "httpVersion",
                                    "cookies",
                                    "headers",
                                    "queryString",
                                    "headersSize",
                                    "bodySize",
                                ],
                                "additionalProperties": False,
                            },
                            "response": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "integer"},
                                    "statusText": {"type": "string"},
                                    "httpVersion": {"type": "string"},
                                    "cookies": {
                                        "type": "array",
                                        "items": COOKIE_SCHEMA,
                                    },
                                    "headers": {
                                        "type": "array",
                                        "items": RECORD_SCHEMA,
                                    },
                                    "content": {
                                        "type": "object",
                                        "properties": {
                                            "size": {"type": "integer"},
                                            "compression": {"type": "number"},
                                            "mimeType": {"type": "string"},
                                            "text": {"type": "string"},
                                            "encoding": {"type": "string"},
                                            "comment": {"type": "string"},
                                        },
                                        "required": ["size"],
                                        "additionalProperties": False,
                                    },
                                    "redirectURL": {"type": "string"},
                                    "headersSize": {"type": "integer"},
                                    "bodySize": {"type": "integer"},
                                    "comment": {"type": "string"},
                                },
                                "required": [
                                    "status",
                                    "statusText",
                                    "httpVersion",
                                    "cookies",
                                    "headers",
                                    "headersSize",
                                    "bodySize",
                                ],
                                "additionalProperties": False,
                            },
                            "cache": {
                                "type": "object",
                                "properties": {
                                    "beforeRequest": CACHE_ENTRY_SCHEMA,
                                    "afterRequest": CACHE_ENTRY_SCHEMA,
                                    "comment": {"type": "string"},
                                },
                                "additionalProperties": False,
                            },
                            "timings": {
                                "type": "object",
                                "properties": {
                                    "dns": {"type": "number"},
                                    "connect": {"type": "number"},
                                    "blocked": {"type": "number"},
                                    "send": {"type": "number"},
                                    "wait": {"type": "number"},
                                    "receive": {"type": "number"},
                                    "ssl": {"type": "number"},
                                    "comment": {"type": "string"},
                                },
                                "required": ["send", "wait", "receive"],
                                "additionalProperties": False,
                            },
                            "serverIPAddress": {"type": "string"},
                            "connection": {"type": "string"},
                            "comment": {"type": "string"},
                        },
                        "required": [
                            "startedDateTime",
                            "time",
                            "request",
                            "response",
                            "timings",
                        ],
                        "additionalProperties": False,
                    },
                },
                "comment": {"type": "string"},
            },
            "required": ["version", "creator", "browser", "entries"],
            "additionalProperties": False,
        }
    },
    "required": ["log"],
    "additionalProperties": False,
}
HAR_VALIDATOR = jsonschema.Draft7Validator(HAR_SCHEMA)


if sys.version_info < (3, 10):
    st.register_type_strategy(
        harfile.Request,
        st.builds(
            harfile.Request,
            bodySize=st.integers(),
            comment=st.text() | st.none(),
            cookies=st.lists(
                st.builds(
                    harfile.Cookie,
                    comment=st.text() | st.none(),
                    domain=st.text() | st.none(),
                    expires=st.text() | st.none(),
                    httpOnly=st.booleans() | st.none(),
                    name=st.text(),
                    path=st.text() | st.none(),
                    secure=st.booleans() | st.none(),
                    value=st.text(),
                )
            ),
            headers=st.lists(
                st.builds(
                    harfile.Record,
                    comment=st.text() | st.none(),
                    name=st.text(),
                    value=st.text(),
                )
            ),
            headersSize=st.integers(),
            httpVersion=st.text(),
            method=st.text(),
            postData=st.builds(
                harfile.PostData,
                comment=st.text() | st.none(),
                mimeType=st.text(),
                params=st.lists(
                    st.builds(
                        harfile.PostParameter,
                        comment=st.text() | st.none(),
                        contentType=st.text() | st.none(),
                        fileName=st.text() | st.none(),
                        name=st.text(),
                        value=st.text() | st.none(),
                    )
                ),
            ),
            queryString=st.lists(
                st.builds(
                    harfile.Record,
                    comment=st.text() | st.none(),
                    name=st.text(),
                    value=st.text(),
                )
            ),
            url=st.text(),
        ),
    )
    st.register_type_strategy(
        harfile.Response,
        st.builds(
            harfile.Response,
            bodySize=st.integers(),
            comment=st.text() | st.none(),
            content=st.builds(
                harfile.Content,
                comment=st.text() | st.none(),
                compression=st.floats(allow_nan=False, allow_infinity=False) | st.integers(),
                encoding=st.text() | st.none(),
                mimeType=st.text() | st.none(),
                size=st.integers(),
                text=st.text() | st.none(),
            ),
            cookies=st.lists(
                st.builds(
                    harfile.Cookie,
                    comment=st.text() | st.none(),
                    domain=st.text() | st.none(),
                    expires=st.text() | st.none(),
                    httpOnly=st.booleans() | st.none(),
                    name=st.text(),
                    path=st.text() | st.none(),
                    secure=st.booleans() | st.none(),
                    value=st.text(),
                )
            ),
            headers=st.lists(
                st.builds(
                    harfile.Record,
                    comment=st.text() | st.none(),
                    name=st.text(),
                    value=st.text(),
                )
            ),
            headersSize=st.integers(),
            httpVersion=st.text(),
            redirectURL=st.text(),
            status=st.integers(),
            statusText=st.text(),
        ),
    )
    st.register_type_strategy(
        harfile.Timings,
        st.builds(
            harfile.Timings,
            blocked=st.floats() | st.integers(),
            comment=st.text() | st.none(),
            connect=st.floats() | st.integers(),
            dns=st.floats() | st.integers(),
            receive=st.floats() | st.integers(),
            send=st.floats() | st.integers(),
            ssl=st.floats() | st.integers(),
            wait=st.floats() | st.integers(),
        ),
    )


ENTRY_STRATEGY = st.fixed_dictionaries(
    {
        "startedDateTime": st.datetimes(timezones=st.just(datetime.timezone.utc)),
        "time": st.floats(min_value=0, allow_nan=False, allow_infinity=False) | st.integers(min_value=0),
        "request": st.from_type(harfile.Request),
        "response": st.from_type(harfile.Response),
        "timings": st.from_type(harfile.Timings),
    },
    optional={
        "cache": st.from_type(harfile.Cache) | st.none(),
        "serverIPAddress": st.text() | st.none(),
        "connection": st.text() | st.none(),
        "comment": st.text() | st.none(),
    },
)


def write_har(arg, entries):
    with harfile.open(arg) as har:
        for entry in entries:
            har.add_entry(**entry)


@given(entries=st.lists(ENTRY_STRATEGY, max_size=10))
@settings(
    phases=[Phase.reuse, Phase.generate, Phase.shrink],
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_write_har(entries, tmp_path):
    buffer = io.StringIO()
    write_har(buffer, entries)
    har = buffer.getvalue()
    HAR_VALIDATOR.validate(json.loads(har))
    path = tmp_path / "test.har"
    write_har(path, entries)
    with open(path) as fd:
        HAR_VALIDATOR.validate(json.load(fd))
    write_har(path, entries)
    with open(path) as fd:
        HAR_VALIDATOR.validate(json.load(fd))


def test_close():
    buffer = io.StringIO()
    with harfile.open(buffer) as har:
        har.close()


def test_exception():
    buffer = io.StringIO()
    with pytest.raises(ZeroDivisionError):
        with harfile.open(buffer):
            raise ZeroDivisionError
    assert buffer.getvalue() == ""


def test_with_comments():
    buffer = io.StringIO()
    with harfile.open(
        buffer,
        creator=harfile.Creator(name="test", version="0.1", comment="EXAMPLE-1"),
        browser=harfile.Browser(name="test", version="0.2", comment="EXAMPLE-2"),
        comment="EXAMPLE-3",
    ):
        pass
    print(buffer.getvalue())
    assert (
        buffer.getvalue()
        == """{
    "log": {
        "version": "1.2",
        "creator": {
            "name": "test",
            "version": "0.1",
            "comment": "EXAMPLE-1"
        },
        "browser": {
            "name": "test",
            "version": "0.2",
            "comment": "EXAMPLE-2"
        },
        "comment": "EXAMPLE-3",
        "entries": []
    }
}"""
    )
    HAR_VALIDATOR.validate(json.loads(buffer.getvalue()))
