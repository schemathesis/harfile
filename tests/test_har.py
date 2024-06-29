import datetime
import io
import json

import harfile
import jsonschema
from hypothesis import HealthCheck, Phase, given, settings
from hypothesis import strategies as st

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
                                                        "contentType": {
                                                            "type": "string"
                                                        },
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

ENTRY_STRATEGY = st.fixed_dictionaries(
    {
        "startedDateTime": st.datetimes(timezones=st.just(datetime.timezone.utc)),
        "time": st.floats(min_value=0, allow_nan=False, allow_infinity=False)
        | st.integers(min_value=0),
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
    suppress_health_check=[HealthCheck.function_scoped_fixture],
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
