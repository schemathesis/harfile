# harfile

[![CI](https://github.com/schemathesis/harfile/actions/workflows/ci.yml/badge.svg)](https://github.com/schemathesis/harfile/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/schemathesis/harfile/branch/main/graph/badge.svg)](https://codecov.io/gh/schemathesis/harfile/branch/main)
[![Version](https://img.shields.io/pypi/v/harfile.svg)](https://pypi.org/project/harfile/)
[![Python versions](https://img.shields.io/pypi/pyversions/harfile.svg)](https://pypi.org/project/harfile/)
[![License](https://img.shields.io/pypi/l/harfile.svg)](https://opensource.org/licenses/MIT)

This package provides a zero-dependency writer for building HAR (HTTP Archive) files in Python.

**NOTES**:

- The writer assumes a single-threaded environment.
- Pages are not supported.
- `add_entry` writes each entry to the file right away. If the `with` block raises, the file keeps the entries written so far and stays valid.
- `add_entry` raises `ValueError` on a closed file and on `NaN` or `Infinity` numbers.
- Naive `datetime` values count as local time.

## Installation

```
pip install harfile
```

## Usage

```python
import datetime
import io

import harfile


# Write to a file
with harfile.open("filename.har") as har:
    har.add_entry(
        startedDateTime=datetime.datetime.now(datetime.timezone.utc),
        time=42,
        request=harfile.Request(
            method="GET",
            url="http://example.com",
            httpVersion="HTTP/1.1",
        ),
        response=harfile.Response(
            status=200,
            statusText="OK",
            httpVersion="HTTP/1.1",
        ),
        timings=harfile.Timings(
            send=0,
            wait=0,
            receive=0,
        ),
    )


# Write to a string buffer
buffer = io.StringIO()
with harfile.open(buffer) as har:
    pass
```

## License

The code in this project is licensed under [MIT license](https://opensource.org/licenses/MIT).
By contributing to `harfile`, you agree that your contributions will be licensed under its MIT license.
