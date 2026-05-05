import unicodedata
import re

def slugify(text: str) -> str:
    """Convert a string to a filesystem-safe slug."""
    # Remove accents
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    # Replace spaces and special chars with underscores
    text = re.sub(r'[^a-zA-Z0-9]+', '_', text)
    # Lowercase and strip
    return text.lower().strip('_')