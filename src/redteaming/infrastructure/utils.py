import re
import unicodedata


def slugify(text: str) -> str:
    """Convert a string to a filesystem-safe slug."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text)
    return text.lower().strip("_")

