from datetime import datetime
import io
import json
import pathlib

import harfile
import pytest

CURRENT_DIR = pathlib.Path(__file__).parent.absolute()

with open(CURRENT_DIR / "entries.json") as fd:
    RAW_ENTRIES = fd.read()
    ENTRIES = json.loads(RAW_ENTRIES)

for entry in ENTRIES:
    entry["startedDateTime"] = datetime.fromisoformat(entry["startedDateTime"])
    entry["request"] = harfile.Request(
        **{
            "method": entry["request"]["method"],
            "url": entry["request"]["url"],
            "httpVersion": entry["request"]["httpVersion"],
            "cookies": [harfile.Cookie(**cookie) for cookie in entry["request"]["cookies"]],
            "headers": [harfile.Record(**header) for header in entry["request"]["headers"]],
            "queryString": [harfile.Record(**query) for query in entry["request"]["queryString"]],
            "headersSize": entry["request"]["headersSize"],
            "bodySize": entry["request"]["bodySize"],
            **({} if "comment" not in entry["request"] else {"comment": entry["request"]["comment"]}),
            **(
                {}
                if "postData" not in entry["request"]
                else {
                    "postData": harfile.PostData(
                        **{
                            "mimeType": entry["request"]["postData"]["mimeType"],
                            **(
                                {}
                                if "params" not in entry["request"]["postData"]
                                else {
                                    "params": [
                                        harfile.PostParameter(**param)
                                        for param in entry["request"]["postData"]["params"]
                                    ]
                                }
                            ),
                            **(
                                {}
                                if "comment" not in entry["request"]["postData"]
                                else {"comment": entry["request"]["postData"]["comment"]}
                            ),
                            **(
                                {}
                                if "text" not in entry["request"]["postData"]
                                else {"text": entry["request"]["postData"]["text"]}
                            ),
                        }
                    )
                }
            ),
        }
    )
    entry["response"] = harfile.Response(
        **{
            "status": entry["response"]["status"],
            "statusText": entry["response"]["statusText"],
            "httpVersion": entry["response"]["httpVersion"],
            "cookies": [harfile.Cookie(**cookie) for cookie in entry["response"]["cookies"]],
            "headers": [harfile.Record(**header) for header in entry["response"]["headers"]],
            "content": harfile.Content(**entry["response"]["content"]),
            "redirectURL": entry["response"]["redirectURL"],
            "headersSize": entry["response"]["headersSize"],
            "bodySize": entry["response"]["bodySize"],
            **({} if "comment" not in entry["response"] else {"comment": entry["response"]["comment"]}),
        }
    )
    entry["timings"] = harfile.Timings(**entry["timings"])
    if "cache" in entry:
        entry["cache"] = harfile.Cache(
            **{
                **(
                    {}
                    if "beforeRequest" not in entry["cache"]
                    else {"beforeRequest": harfile.CacheEntry(**entry["cache"]["beforeRequest"])}
                ),
                **(
                    {}
                    if "afterRequest" not in entry["cache"]
                    else {"afterRequest": harfile.CacheEntry(**entry["cache"]["afterRequest"])}
                ),
                **({} if "comment" not in entry["cache"] else {"comment": entry["cache"]["comment"]}),
            }
        )

buffer = io.StringIO()
with harfile.open(buffer) as har:
    for entry in ENTRIES:
        har.add_entry(**entry)
loaded = json.dumps(json.loads(buffer.getvalue())["log"]["entries"])
assert len(loaded) == len(RAW_ENTRIES.strip())


@pytest.mark.benchmark
def test_writing_har():
    buffer = io.StringIO()
    with harfile.open(buffer) as har:
        for entry in ENTRIES:
            har.add_entry(**entry)
