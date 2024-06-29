from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Creator:
    # Name of the application used to export the log
    name: str
    # Version of the application used to export the log
    version: str
    comment: str | None = None


@dataclass
class Browser:
    # Name of the browser used to export the log
    name: str
    # Version of the browser used to export the log
    version: str
    comment: str | None = None


@dataclass
class Cache:
    """Info about a request coming from browser cache."""

    # State of a cache entry before the request
    beforeRequest: CacheEntry | None = None
    # State of a cache entry after the request
    afterRequest: CacheEntry | None = None
    comment: str | None = None


@dataclass
class CacheEntry:
    # Expiration time of the cache entry
    expires: str
    # The last time the cache entry was opened
    lastAccess: str
    eTag: str
    # The number of times the cache entry has been opened
    hitCount: int
    comment: str | None = None


@dataclass
class Request:
    method: str
    # Absolute URL of the request (fragments are not included)
    url: str
    # Request HTTP Version
    httpVersion: str
    cookies: list[Cookie] = field(default_factory=list)
    headers: list[Record] = field(default_factory=list)
    queryString: list[Record] = field(default_factory=list)
    postData: PostData | None = None
    # Total number of bytes from the start of the HTTP request message until (and including) the double CRLF
    # before the body
    headersSize: int = -1
    # Size of the request body (POST data payload) in bytes
    bodySize: int = -1
    comment: str | None = None


@dataclass
class Cookie:
    # The name of the cookie
    name: str
    # The cookie value
    value: str
    # The path pertaining to the cookie
    path: str | None = None
    # The host of the cookie
    domain: str | None = None
    # Cookie expiration time
    expires: str | None = None
    # Set to true if the cookie is HTTP only, false otherwise
    httpOnly: bool | None = None
    # True if the cookie was transmitted over ssl, false otherwise
    secure: bool | None = None
    comment: str | None = None


@dataclass
class Record:
    name: str
    value: str
    comment: str | None = None


@dataclass
class PostData:
    # MIME type of the posted data
    mimeType: str
    # List of posted parameters (in case of URL encoded parameters)
    params: list[PostParameter] | None = None
    # Plain text posted data
    text: str | None = None
    comment: str | None = None


@dataclass
class PostParameter:
    name: str
    value: str | None = None
    fileName: str | None = None
    contentType: str | None = None
    comment: str | None = None


@dataclass
class Content:
    size: int = 0
    # Number of bytes saved
    compression: int | float | None = None
    # MIME type of the response text (value of the Content-Type response header).
    # The charset attribute of the MIME type is included
    mimeType: str | None = None
    # Response body sent from the server or loaded from the browser cache.
    # This field is populated with textual content only.
    # The text field is either HTTP decoded text or a encoded (e.g. "base64") representation of the response body
    text: str | None = None
    encoding: str | None = None
    # Encoding used for response text field e.g "base64"
    comment: str | None = None


@dataclass
class Response:
    # Response status
    status: int
    # Response status description
    statusText: str
    # Response HTTP Version
    httpVersion: str
    cookies: list[Cookie] = field(default_factory=list)
    headers: list[Record] = field(default_factory=list)
    # Details about the response body
    content: Content = field(default_factory=Content)
    # Redirection target URL from the Location response header
    redirectURL: str = ""
    # Total number of bytes from the start of the HTTP response message
    # until (and including) the double CRLF before the body
    headersSize: int = -1
    # Size of the received response body in bytes
    bodySize: int = -1
    comment: str | None = None


@dataclass
class Timings:
    # Time required to send HTTP request to the server
    send: int | float
    # Waiting for a response from the server
    wait: int | float
    # Time required to read entire response from the server (or cache)
    receive: int | float
    # Time spent in a queue waiting for a network connection
    blocked: int | float = -1
    # DNS resolution time. The time required to resolve a host name
    dns: int | float = -1
    # Time required to create TCP connection
    connect: int | float = -1
    # Time required for SSL/TLS negotiation
    ssl: int | float = -1
    comment: str | None = None
