import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

TEXT_EXT = {".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".tsx", ".jsx", ".swift", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".html", ".css", ".yml", ".yaml", ".toml", ".sh", ".sql"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_EXT = TEXT_EXT | IMAGE_EXT | {".pdf", ".docx"}
ROLES = ("mandatory_requirement", "factual_source", "example_output", "visual_inspiration", "background", "negative_example")


def safe_name(name: str) -> str:
    return re.sub(r"[^\w.\- ]", "_", Path(name).name)[:200] or "file"


def extract(name: str, data: bytes) -> tuple[str, str, list[str]]:
    """returns (text, extraction_status, warnings). Never executes content."""
    ext = Path(name).suffix.lower()
    if ext in TEXT_EXT:
        return data.decode("utf-8", errors="replace"), "ok", []
    if ext == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if sum(i.file_size for i in z.infolist()) > 50 * 1024 * 1024:
                    return "", "unsupported", ["docx expands too large"]
                root = ET.fromstring(z.read("word/document.xml"))
            ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            paras = ["".join(t.text or "" for t in p.iter(ns + "t")) for p in root.iter(ns + "p")]
            return "\n".join(paras), "ok", []
        except Exception:
            return "", "unsupported", ["could not parse docx"]
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
            return text, ("ok" if text.strip() else "empty"), ([] if text.strip() else ["no extractable text (scanned PDF?)"])
        except ImportError:
            return "", "unsupported", ["PDF text extraction needs the optional 'pypdf' package; file stored but not readable by the model"]
        except Exception:
            return "", "unsupported", ["could not parse pdf"]
    if ext in IMAGE_EXT:
        return "", "unsupported", ["image stored; no text extraction (visual content is not sent to the model in this version)"]
    return "", "unsupported", ["unsupported file type"]
