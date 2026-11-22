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
                mimeType=st.text(),
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
            blocked=st.floats(allow_nan=False, allow_infinity=False) | st.integers(),
            comment=st.text() | st.none(),
            connect=st.floats(allow_nan=False, allow_infinity=False) | st.integers(),
            dns=st.floats(allow_nan=False, allow_infinity=False) | st.integers(),
            receive=st.floats(allow_nan=False, allow_infinity=False) | st.integers(),
            send=st.floats(allow_nan=False, allow_infinity=False) | st.integers(),
            ssl=st.floats(allow_nan=False, allow_infinity=False) | st.integers(),
            wait=st.floats(allow_nan=False, allow_infinity=False) | st.integers(),
        ),
    )

st.register_type_strategy(float, st.floats(allow_nan=False, allow_infinity=False))


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
    deadline=None,
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
    assert har.closed


@pytest.mark.parametrize("explicit_close", [True, False], ids=["close", "with-block"])
def test_add_entry_after_close(explicit_close):
    buffer = io.StringIO()
    if explicit_close:
        har = harfile.open(buffer)
        har.close()
    else:
        with harfile.open(buffer) as har:
            pass
    expected = buffer.getvalue()
    with pytest.raises(ValueError, match="closed file"):
        har.add_entry(
            startedDateTime="2024-01-01T00:00:00+00:00",
            time=1,
            request=harfile.Request(method="GET", url="http://127.0.0.1/", httpVersion="HTTP/1.1"),
            response=harfile.Response(status=200, statusText="OK", httpVersion="HTTP/1.1"),
            timings=harfile.Timings(send=0, wait=0, receive=0),
        )
    assert buffer.getvalue() == expected
    HAR_VALIDATOR.validate(json.loads(expected))


def test_exception():
    buffer = io.StringIO()
    with pytest.raises(ZeroDivisionError):
        with harfile.open(buffer) as har:
            raise ZeroDivisionError
    assert har.closed
    assert buffer.getvalue() == ""


@pytest.mark.parametrize("managed", [False, True])
def test_exception_after_entry(managed, tmp_path):
    path = tmp_path / "test.har"
    target = path if managed else io.StringIO()
    with pytest.raises(ZeroDivisionError):
        with harfile.open(target) as har:
            har.add_entry(
                startedDateTime="2026-01-01T00:00:00+00:00",
                time=1,
                request=harfile.Request(method="GET", url="http://127.0.0.1/", httpVersion="HTTP/1.1"),
                response=harfile.Response(status=200, statusText="OK", httpVersion="HTTP/1.1"),
                timings=harfile.Timings(send=0, wait=0, receive=0),
            )
            raise ZeroDivisionError
    assert har.closed
    output = path.read_text() if managed else target.getvalue()
    data = json.loads(output)
    HAR_VALIDATOR.validate(data)
    assert len(data["log"]["entries"]) == 1


@pytest.mark.parametrize("explicit_close", [True, False], ids=["close", "with-block"])
def test_close_write_error_closes_managed_fd(explicit_close, monkeypatch, tmp_path):
    har = harfile.open(tmp_path / "test.har")
    fd = har._fd

    def write(_):
        raise OSError("disk full")

    monkeypatch.setattr(fd, "write", write)
    with pytest.raises(OSError, match="disk full"):
        if explicit_close:
            har.close()
        else:
            with har:
                pass
    assert har.closed
    assert fd.closed


def test_with_comments():
    buffer = io.StringIO()
    with harfile.open(
        buffer,
        creator=harfile.Creator(name="test", version="0.1", comment="EXAMPLE-1"),
        browser=harfile.Browser(name="test", version="0.2", comment="EXAMPLE-2"),
        comment="EXAMPLE-3",
    ):
        pass
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


VALUE_NEEDING_ESCAPING = 'say "hi"\\\n'


@pytest.mark.parametrize(
    ("kwargs", "path"),
    [
        ({"comment": VALUE_NEEDING_ESCAPING}, ("comment",)),
        ({"creator": harfile.Creator(name=VALUE_NEEDING_ESCAPING, version="1")}, ("creator", "name")),
        ({"creator": harfile.Creator(name="test", version=VALUE_NEEDING_ESCAPING)}, ("creator", "version")),
        (
            {"creator": harfile.Creator(name="test", version="1", comment=VALUE_NEEDING_ESCAPING)},
            ("creator", "comment"),
        ),
        ({"browser": harfile.Browser(name=VALUE_NEEDING_ESCAPING, version="1")}, ("browser", "name")),
        ({"browser": harfile.Browser(name="test", version=VALUE_NEEDING_ESCAPING)}, ("browser", "version")),
        (
            {"browser": harfile.Browser(name="test", version="1", comment=VALUE_NEEDING_ESCAPING)},
            ("browser", "comment"),
        ),
    ],
    ids=[
        "comment",
        "creator-name",
        "creator-version",
        "creator-comment",
        "browser-name",
        "browser-version",
        "browser-comment",
    ],
)
def test_header_values_are_escaped(kwargs, path):
    buffer = io.StringIO()
    with harfile.open(buffer, **kwargs):
        pass
    value = json.loads(buffer.getvalue())["log"]
    for key in path:
        value = value[key]
    assert value == VALUE_NEEDING_ESCAPING


def test_started_date_time_string_is_escaped():
    buffer = io.StringIO()
    with harfile.open(buffer) as har:
        har.add_entry(
            startedDateTime=VALUE_NEEDING_ESCAPING,
            time=1,
            request=harfile.Request(method="GET", url="http://127.0.0.1/", httpVersion="HTTP/1.1"),
            response=harfile.Response(status=200, statusText="OK", httpVersion="HTTP/1.1"),
            timings=harfile.Timings(send=0, wait=0, receive=0),
        )
    assert json.loads(buffer.getvalue())["log"]["entries"][0]["startedDateTime"] == VALUE_NEEDING_ESCAPING


def test_naive_started_date_time_gets_utc_offset():
    naive = datetime.datetime(2026, 11, 16, 16, 28, 51, 75318)
    buffer = io.StringIO()
    with harfile.open(buffer) as har:
        har.add_entry(
            startedDateTime=naive,
            time=1,
            request=harfile.Request(method="GET", url="http://127.0.0.1/", httpVersion="HTTP/1.1"),
            response=harfile.Response(status=200, statusText="OK", httpVersion="HTTP/1.1"),
            timings=harfile.Timings(send=0, wait=0, receive=0),
        )
    parsed = datetime.datetime.fromisoformat(json.loads(buffer.getvalue())["log"]["entries"][0]["startedDateTime"])
    assert parsed == naive.astimezone()


def test_encode_matches_json_dumps():
    sample = {
        "text": VALUE_NEEDING_ESCAPING,
        "unicode": "café 日本語 \U0001f600  ",
        "control": '\x00\x1f\t\r\n\\ "/',
        "nested": [{"a": [1, 2.5, -1e100, True, False, None], "b": {}}, [], ""],
    }
    assert harfile._encode(sample) == json.dumps(sample)


def _add_entry(har, *, time=1, send=0):
    har.add_entry(
        startedDateTime="2024-01-01T00:00:00+00:00",
        time=time,
        request=harfile.Request(method="GET", url="http://127.0.0.1/", httpVersion="HTTP/1.1"),
        response=harfile.Response(status=200, statusText="OK", httpVersion="HTTP/1.1"),
        timings=harfile.Timings(send=send, wait=0, receive=0),
    )


@pytest.mark.parametrize("field", ["time", "send"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")], ids=["nan", "inf", "-inf"])
def test_non_finite_floats_are_rejected(field, value):
    buffer = io.StringIO()
    with harfile.open(buffer) as har:
        with pytest.raises(ValueError, match="not JSON compliant"):
            _add_entry(har, **{field: value})
        _add_entry(har)
    assert len(json.loads(buffer.getvalue())["log"]["entries"]) == 1
