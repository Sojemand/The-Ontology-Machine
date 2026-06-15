from urllib.parse import quote

from .errors import deny
from .scope import resolve_candidate_path


class ReadOnlySqliteConnection:
    def __init__(self, connection):
        self._connection = connection

    def __getattr__(self, name):
        if name in {"enable_load_extension", "load_extension"}:
            deny("Python workbench blockiert SQLite-Erweiterungen.")
        return getattr(self._connection, name)

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._connection.__exit__(exc_type, exc, tb)


def create_restricted_sqlite_connect(original_sqlite_connect):
    def restricted_sqlite_connect(database, *args, **kwargs):
        if database == ":memory:":
            kwargs.pop("uri", None)
            return ReadOnlySqliteConnection(original_sqlite_connect(database, *args, **kwargs))

        resolved = resolve_candidate_path(database)
        kwargs.pop("uri", None)
        readonly_uri = f"file:///{quote(resolved.as_posix(), safe='/:')}?mode=ro"
        connection = original_sqlite_connect(readonly_uri, *args, uri=True, **kwargs)
        connection.enable_load_extension(False)
        return ReadOnlySqliteConnection(connection)

    return restricted_sqlite_connect
