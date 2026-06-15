"""Format and block-type constants for file optimizer document models."""
from __future__ import annotations


class FileFormat:
    MSG = "msg"
    EML = "eml"
    EMLX = "emlx"
    MBOX = "mbox"
    OFT = "oft"
    PST = "pst"
    OST = "ost"
    XLSX = "xlsx"
    XLS = "xls"
    XLSB = "xlsb"
    XLSM = "xlsm"
    ODS = "ods"
    DOCX = "docx"
    DOC = "doc"
    ODT = "odt"
    RTF = "rtf"
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    CONFIG = "config"
    CAD = "cad"
    ZIP = "zip"
    UNKNOWN = "unknown"

    ALL = [MSG, EML, EMLX, MBOX, OFT, PST, OST, XLSX, XLS, XLSB, XLSM, ODS, DOCX, DOC, ODT, RTF, PDF, IMAGE, TEXT, CONFIG, CAD, ZIP, UNKNOWN]
    MAIL_FORMATS = {MSG, EML, EMLX, MBOX, OFT, PST, OST}
    EXT_MAP: dict[str, str] = {
        ".msg": MSG,
        ".eml": EML,
        ".emlx": EMLX,
        ".mbox": MBOX,
        ".oft": OFT,
        ".pst": PST,
        ".ost": OST,
        ".xlsx": XLSX,
        ".xls": XLS,
        ".xlsb": XLSB,
        ".xlsm": XLSM,
        ".ods": ODS,
        ".docx": DOCX,
        ".doc": DOC,
        ".odt": ODT,
        ".rtf": RTF,
        ".pdf": PDF,
        ".jpg": IMAGE,
        ".jpeg": IMAGE,
        ".png": IMAGE,
        ".tif": IMAGE,
        ".tiff": IMAGE,
        ".bmp": IMAGE,
        ".webp": IMAGE,
        ".txt": TEXT,
        ".text": TEXT,
        ".md": TEXT,
        ".markdown": TEXT,
        ".rst": TEXT,
        ".log": TEXT,
        ".tex": TEXT,
        ".yaml": CONFIG,
        ".yml": CONFIG,
        ".toml": CONFIG,
        ".ini": CONFIG,
        ".cfg": CONFIG,
        ".conf": CONFIG,
        ".env": CONFIG,
        ".properties": CONFIG,
        ".dwg": CAD,
        ".dxf": CAD,
        ".zip": ZIP,
    }

    @staticmethod
    def from_ext(ext: str) -> str:
        return FileFormat.EXT_MAP.get(ext.lower(), FileFormat.UNKNOWN)

    @staticmethod
    def is_mail_format(fmt: str) -> bool:
        return str(fmt).lower() in FileFormat.MAIL_FORMATS


class ValueType:
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    FORMULA = "formula"
    BOOLEAN = "boolean"
    EMPTY = "empty"
    CURRENCY = "currency"


class BlockType:
    CELL = "cell"
    PARAGRAPH = "paragraph"
    HEADER = "header"
    LIST_ITEM = "list_item"
    CODE_BLOCK = "code_block"
    CONFIG_SECTION = "config_section"
    TABLE_CELL = "table_cell"
    TABLE_ROW = "table_row"
    EMAIL_FIELD = "email_field"
    METADATA = "metadata"
    CHAT_MESSAGE = "chat_message"
    TRANSCRIPT_SEGMENT = "transcript_segment"
