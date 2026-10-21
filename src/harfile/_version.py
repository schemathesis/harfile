from importlib import metadata

try:
    VERSION = metadata.version("harfile")
except metadata.PackageNotFoundError:
    # Local run without installation
    VERSION = "dev"
