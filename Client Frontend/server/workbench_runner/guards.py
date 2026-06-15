import builtins
import os
import pathlib
import socket
import sqlite3
import subprocess
import sys

from .errors import deny
from .scope import ALLOWED_ENV_VARS, BLOCKED_IMPORT_ROOTS, ensure_read_only_mode, resolve_candidate_path
from .sqlite_guard import create_restricted_sqlite_connect


def install_guards() -> None:
    original_open = builtins.open
    original_os_open = os.open
    original_scandir = os.scandir
    original_listdir = os.listdir
    original_stat = os.stat
    original_walk = os.walk
    original_import = builtins.__import__
    original_socket_type = socket.socket

    def restricted_open(file, mode="r", *args, **kwargs):
        return original_open(resolve_candidate_path(file), ensure_read_only_mode(mode), *args, **kwargs)

    def restricted_path_open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        return restricted_open(self, mode=mode, buffering=buffering, encoding=encoding, errors=errors, newline=newline)

    def restricted_read_text(self, encoding=None, errors=None):
        with restricted_open(self, "r", encoding=encoding, errors=errors) as handle:
            return handle.read()

    def restricted_read_bytes(self):
        with restricted_open(self, "rb") as handle:
            return handle.read()

    def deny_mutation(*_args, **_kwargs):
        deny("Python workbench ist read-only.")

    def restricted_os_open(pathname, flags, mode=0o777, *, dir_fd=None):
        if dir_fd is not None:
            deny("Python workbench blockiert dir_fd-Zugriffe.")
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC):
            deny("Python workbench ist read-only.")
        return original_os_open(str(resolve_candidate_path(pathname)), flags, mode)

    def restricted_scandir(pathname="."):
        return original_scandir(str(resolve_candidate_path(pathname)))

    def restricted_listdir(pathname="."):
        return original_listdir(str(resolve_candidate_path(pathname)))

    def restricted_stat(pathname, *args, **kwargs):
        return original_stat(str(resolve_candidate_path(pathname)), *args, **kwargs)

    def restricted_walk(top, *args, **kwargs):
        return original_walk(str(resolve_candidate_path(top)), *args, **kwargs)

    def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
        root_name = str(name or "").split(".", 1)[0]
        if root_name in BLOCKED_IMPORT_ROOTS:
            deny(f"Python workbench blockiert das Modul {root_name}.")
        return original_import(name, globals, locals, fromlist, level)

    def blocked_socket(*_args, **_kwargs):
        deny("Python workbench blockiert Netzwerkzugriffe.")

    class BlockedSocket(original_socket_type):
        def __new__(cls, *_args, **_kwargs):
            deny("Python workbench blockiert Netzwerkzugriffe.")

    def blocked_subprocess(*_args, **_kwargs):
        deny("Python workbench blockiert Prozessstarts.")

    def audit(event, args):
        if event == "open" and args:
            ensure_read_only_mode(args[1] if len(args) > 1 else "r")
            resolve_candidate_path(args[0])
            return
        if event.startswith("socket."):
            deny("Python workbench blockiert Netzwerkzugriffe.")
        if event.startswith("subprocess."):
            deny("Python workbench blockiert Prozessstarts.")
        if event.startswith("ctypes.") or event.startswith("winreg."):
            deny("Python workbench blockiert native und Registry-Zugriffe.")
        if event in {"os.remove", "os.rename", "os.replace", "os.rmdir", "os.chdir"}:
            deny("Python workbench ist read-only.")

    preserved = {key: value for key, value in os.environ.items() if key in ALLOWED_ENV_VARS}
    os.environ.clear()
    os.environ.update(preserved)
    sys.dont_write_bytecode = True
    sys.addaudithook(audit)

    builtins.__import__ = restricted_import
    builtins.open = restricted_open
    pathlib.Path.open = restricted_path_open
    pathlib.Path.read_text = restricted_read_text
    pathlib.Path.read_bytes = restricted_read_bytes
    pathlib.Path.write_text = deny_mutation
    pathlib.Path.write_bytes = deny_mutation
    pathlib.Path.unlink = deny_mutation
    pathlib.Path.rename = deny_mutation
    pathlib.Path.replace = deny_mutation
    pathlib.Path.mkdir = deny_mutation
    pathlib.Path.rmdir = deny_mutation
    pathlib.Path.touch = deny_mutation
    pathlib.Path.chmod = deny_mutation

    os.open = restricted_os_open
    os.remove = deny_mutation
    os.unlink = deny_mutation
    os.rename = deny_mutation
    os.replace = deny_mutation
    os.rmdir = deny_mutation
    os.chdir = deny_mutation
    os.makedirs = deny_mutation
    os.mkdir = deny_mutation
    os.stat = restricted_stat
    os.listdir = restricted_listdir
    os.scandir = restricted_scandir
    os.walk = restricted_walk
    if hasattr(os, "startfile"):
        os.startfile = deny_mutation

    socket.socket = BlockedSocket
    socket.create_connection = blocked_socket
    if hasattr(socket, "create_server"):
        socket.create_server = blocked_socket

    subprocess.Popen = blocked_subprocess
    subprocess.call = blocked_subprocess
    subprocess.run = blocked_subprocess
    subprocess.check_call = blocked_subprocess
    subprocess.check_output = blocked_subprocess
    sqlite3.connect = create_restricted_sqlite_connect(sqlite3.connect)
