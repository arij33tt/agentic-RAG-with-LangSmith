import re
import logging
import ftfy

logger = logging.getLogger(__name__)


class TextCleaner:
    """
    Normalizes raw text extracted by loaders before it's chunked.
    Runs between loaders.py and the chunking step in pipeline.py.
    """

    def __init__(
        self,
        remove_boilerplate_patterns: list[str] | None = None,
    ):
        # regex patterns for common repeated junk (page numbers, headers/footers)
        
        self.boilerplate_patterns = remove_boilerplate_patterns or [
            r"Page \d+ of \d+",
            r"^\s*\d+\s*$",  # longpage no.            
            r"Confidential\s*[-–]\s*Do Not Distribute",
        ]

    def clean(self, text: str) -> str:
        if not text or not text.strip():
            return ""

        text = self._fix_encoding(text)
        text = self._remove_boilerplate(text)
        text = self._fix_hyphenation(text)
        text = self._normalize_whitespace(text)

        return text.strip()

    def _fix_encoding(self, text: str) -> str:
        # repairs mangled unicode from bad PDF/HTML encoding
        return ftfy.fix_text(text)

    def _remove_boilerplate(self, text: str) -> str:
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in self.boilerplate_patterns):
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def _fix_hyphenation(self, text: str) -> str:
        # PDFs often break words across lines with a hyphen, e.g.:
        # "informa-\ntion" should become "information"
        return re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

    def _normalize_whitespace(self, text: str) -> str:
        # collapse 3+ blank lines down to 2 (preserve paragraph breaks,
        # remove excessive gaps), and collapse repeated spaces/tabs
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text