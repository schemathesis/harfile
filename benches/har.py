from datetime import datetime
import io
import json
import pathlib

import harfile
import pytest

CURRENT_DIR = pathlib.Path(__file__).parent.absolute()

with open(CURRENT_DIR / "entries.json") as fd:
    ENTRIES = json.load(fd)

for entry in ENTRIES:
    entry["startedDateTime"] = datetime.fromisoformat(entry["startedDateTime"])
    entry["request"] = harfile.Request(**entry["request"])
    entry["response"] = harfile.Response(**entry["response"])
    entry["timings"] = harfile.Timings(**entry["timings"])
    if "cache" in entry:
        entry["cache"] = harfile.Cache(**entry["cache"])


@pytest.mark.benchmark
def test_writing_har():
    buffer = io.StringIO()
    with harfile.open(buffer) as har:
        for entry in ENTRIES:
            har.add_entry(**entry)
