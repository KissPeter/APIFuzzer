__version__ = "0.9.13"


def _ensure_pkg_resources():
    """Provide a minimal ``pkg_resources`` shim when setuptools ≥ 82 is installed.

    setuptools 82 removed the ``pkg_resources`` module, but kittyfuzzer
    still does ``from pkg_resources import get_distribution`` at import
    time.  This injects a lightweight adapter backed by
    ``importlib.metadata`` so the import succeeds on every Python ≥ 3.10.
    """
    try:
        import pkg_resources  # noqa: F401 – already available, nothing to do
        return
    except ImportError:
        pass

    import importlib.metadata
    import sys
    import types

    shim = types.ModuleType("pkg_resources")
    shim.__doc__ = "Minimal pkg_resources shim (setuptools ≥ 82 compat)"

    class _Distribution:
        """Tiny stand-in for pkg_resources.Distribution."""
        def __init__(self, dist):
            self._dist = dist

        @property
        def version(self):
            return self._dist.version

        @property
        def project_name(self):
            return self._dist.metadata["Name"]

    class DistributionNotFound(Exception):
        pass

    def get_distribution(name):
        try:
            return _Distribution(importlib.metadata.distribution(name))
        except importlib.metadata.PackageNotFoundError as exc:
            raise DistributionNotFound(str(exc)) from exc

    def require(*_args, **_kwargs):
        pass  # no-op; kittyfuzzer never calls this

    shim.get_distribution = get_distribution
    shim.DistributionNotFound = DistributionNotFound
    shim.require = require

    sys.modules["pkg_resources"] = shim


_ensure_pkg_resources()

