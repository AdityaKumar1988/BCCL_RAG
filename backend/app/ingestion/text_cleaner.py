import re

class TextCleaner:
    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        
        # Replace non-breaking spaces and unusual whitespace
        cleaned = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
        
        # Remove null bytes
        cleaned = cleaned.replace("\x00", "")
        
        # Fix hyphens at end of line (word wrapping)
        cleaned = re.sub(r"(\w+)-\n(\w+)", r"\1\2", cleaned)
        
        # Normalize multiple spaces (preserving newlines)
        lines = []
        for line in cleaned.split("\n"):
            line = re.sub(r"[ \t]+", " ", line).strip()
            lines.append(line)
            
        # Recombine while collapsing excessive blank lines
        cleaned_text = "\n".join(lines)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
        
        return cleaned_text.strip()
