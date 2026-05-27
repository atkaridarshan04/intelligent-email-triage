"""attachment_features.py — presence, type, executable, macro detection."""
from src.datasets.schema import EmailRecord

_EXECUTABLES = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".vbs", ".js", ".jar", ".msi", ".scr", ".com"}
_MACROS = {".xlsm", ".docm", ".pptm", ".xltm", ".dotm", ".xlam"}
_ARCHIVES = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".iso"}


def extract(rec: EmailRecord) -> None:
    if not rec.attachments:
        return

    rec.has_attachment = True
    types = set()

    for att in rec.attachments:
        ext = ("." + att.filename.rsplit(".", 1)[-1]).lower() if "." in att.filename else ""
        mime = att.mime_type.lower()

        if ext in _EXECUTABLES or "executable" in mime or "x-msdownload" in mime:
            rec.executable_detected = True
            types.add("executable")
        elif ext in _MACROS or "macro" in mime:
            rec.macro_detected = True
            types.add("macro")
        elif ext in _ARCHIVES or "zip" in mime or "compressed" in mime:
            types.add("archive")
        elif "pdf" in mime or ext == ".pdf":
            types.add("pdf")
        elif "office" in mime or ext in {".doc", ".xls", ".ppt", ".docx", ".xlsx", ".pptx"}:
            types.add("office")
        else:
            types.add("other")

    rec.attachment_type = ",".join(sorted(types))
