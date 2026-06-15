from __future__ import annotations

import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import customtkinter  # noqa: F401
except ModuleNotFoundError:
    ctk = types.ModuleType("customtkinter")

    class _Widget:
        def __init__(self, *args, **kwargs):
            self._value = kwargs.get("text", "")
            self._config = dict(kwargs)
            self._children = []

        def pack(self, *args, **kwargs):
            return None

        def pack_forget(self):
            return None

        def grid(self, *args, **kwargs):
            return None

        def grid_forget(self):
            return None

        def grid_columnconfigure(self, *args, **kwargs):
            return None

        def place(self, *args, **kwargs):
            return None

        def add(self, *args, **kwargs):
            return _Widget()

        def insert(self, *args, **kwargs):
            if args:
                self._value = args[-1]

        def delete(self, *args, **kwargs):
            self._value = ""

        def get(self):
            return self._value

        def set(self, value):
            self._value = value

        def configure(self, **kwargs):
            self._config.update(kwargs)
            if "text" in kwargs:
                self._value = kwargs["text"]

        def cget(self, key):
            return self._config.get(key)

        def bind(self, *args, **kwargs):
            return None

        def destroy(self):
            return None

        def winfo_children(self):
            return list(self._children)

        def winfo_width(self):
            return 1280

        def see(self, *args, **kwargs):
            return None

    class _Tabview(_Widget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._tabs = []
            self._current = ""
            self._command = kwargs.get("command")

        def add(self, name):
            self._tabs.append(name)
            return _Widget()

        def set(self, value):
            self._current = value
            if callable(self._command):
                self._command()

        def get(self):
            return self._current

    class _App(_Widget):
        def title(self, *args, **kwargs):
            return None

        def geometry(self, *args, **kwargs):
            return None

        def minsize(self, *args, **kwargs):
            return None

        def protocol(self, *args, **kwargs):
            return None

        def bind(self, *args, **kwargs):
            return None

        def winfo_screenwidth(self):
            return 1366

        def winfo_screenheight(self):
            return 768

        def after(self, _delay, callback=None, *args):
            if callback:
                callback(*args)

        def mainloop(self):
            return None

    class _Var:
        def __init__(self, value=None):
            self._value = value

        def get(self):
            return self._value

        def set(self, value):
            self._value = value

    ctk.CTk = _App
    ctk.CTkButton = _Widget
    ctk.CTkCheckBox = _Widget
    ctk.CTkEntry = _Widget
    ctk.CTkFrame = _Widget
    ctk.CTkLabel = _Widget
    ctk.CTkOptionMenu = _Widget
    ctk.CTkProgressBar = _Widget
    ctk.CTkScrollableFrame = _Widget
    ctk.CTkSegmentedButton = _Widget
    ctk.CTkSwitch = _Widget
    ctk.CTkTabview = _Tabview
    ctk.CTkTextbox = _Widget
    ctk.BooleanVar = _Var
    ctk.StringVar = _Var
    ctk.set_appearance_mode = lambda *args, **kwargs: None
    ctk.set_default_color_theme = lambda *args, **kwargs: None
    sys.modules["customtkinter"] = ctk

