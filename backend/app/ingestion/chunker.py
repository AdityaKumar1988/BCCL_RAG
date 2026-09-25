import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from backend.app.core.config import settings
from backend.app.ingestion.pdf_parser import ParsedPage

@dataclass
class ChunkMetadata:
    chunk_index: int
    page_number: int
    rule_number: Optional[str]
    section_title: Optional[str]
    content: str
    token_count: int

class StructureAwareChunker:
    """
    Structure-aware chunker tailored for enterprise governance, legal, and operational documents.
    Detects Rule headers, Chapters, numbered sub-clauses, and paragraphs.
    Preserves rule boundaries to prevent fragmenting legal provisions across chunks.
    """
    def __init__(self, target_chunk_size: int = None, chunk_overlap: int = None, min_chunk_size: int = None):
        self.target_chunk_size = target_chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.min_chunk_size = min_chunk_size or settings.MIN_CHUNK_LENGTH

        # Regex patterns for BCCL / CIL organizational document structure
        self.rule_pattern = re.compile(r"(Rule\s+\d+[:\s\w\(\)]*)", re.IGNORECASE)
        self.chapter_pattern = re.compile(r"(CHAPTER\s+[IVXLCDM\d]+[:\s\w\-]*)", re.IGNORECASE)
        self.clause_pattern = re.compile(r"(\(\d+\)|\([a-z]\)|\d+\.\d+)", re.IGNORECASE)

    def chunk_pages(self, pages: List[ParsedPage]) -> List[ChunkMetadata]:
        all_chunks: List[ChunkMetadata] = []
        global_chunk_idx = 0

        current_chapter = "General"
        current_rule = None

        for page in pages:
            if not page.text.strip():
                continue

            # Split page text into structural sections
            lines = page.text.split("\n")
            current_section_lines = []
            current_section_title = current_chapter

            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue

                # Check if new Chapter
                chapter_match = self.chapter_pattern.search(line_str)
                if chapter_match:
                    current_chapter = chapter_match.group(1).strip()
                    current_section_title = current_chapter

                # Check if new Rule
                rule_match = self.rule_pattern.search(line_str)
                if rule_match:
                    # Flush previous rule/section if it has enough content
                    if current_section_lines:
                        section_text = "\n".join(current_section_lines).strip()
                        if len(section_text) >= self.min_chunk_size:
                            chunks = self._sub_chunk(
                                text=section_text,
                                page_number=page.page_number,
                                rule_number=current_rule,
                                section_title=current_section_title,
                                start_idx=global_chunk_idx
                            )
                            all_chunks.extend(chunks)
                            global_chunk_idx += len(chunks)
                        current_section_lines = []

                    # Extract rule identifier (e.g. "Rule 5", "Rule 26")
                    rule_clean = re.match(r"(Rule\s+\d+)", line_str, re.IGNORECASE)
                    current_rule = rule_clean.group(1).title() if rule_clean else line_str[:30]
                    current_section_title = f"{current_chapter} - {line_str}"

                current_section_lines.append(line_str)

            # Flush remaining lines from page
            if current_section_lines:
                section_text = "\n".join(current_section_lines).strip()
                if len(section_text) >= self.min_chunk_size:
                    chunks = self._sub_chunk(
                        text=section_text,
                        page_number=page.page_number,
                        rule_number=current_rule,
                        section_title=current_section_title,
                        start_idx=global_chunk_idx
                    )
                    all_chunks.extend(chunks)
                    global_chunk_idx += len(chunks)

        return all_chunks

    def _sub_chunk(self, text: str, page_number: int, rule_number: Optional[str], section_title: Optional[str], start_idx: int) -> List[ChunkMetadata]:
        """
        Sub-splits text if larger than target size while respecting paragraph/sentence/clause boundaries and maintaining overlap.
        """
        if len(text) <= self.target_chunk_size * 1.5:
            # Fits in a single structure chunk
            token_est = len(text.split())
            return [ChunkMetadata(
                chunk_index=start_idx,
                page_number=page_number,
                rule_number=rule_number,
                section_title=section_title,
                content=text,
                token_count=token_est
            )]

        # If too large, split into paragraph or clause blocks with overlap
        paragraphs = text.split("\n\n")
        if len(paragraphs) == 1:
            paragraphs = text.split("\n")

        chunks: List[ChunkMetadata] = []
        current_chunk_text = ""
        sub_idx = start_idx

        for p in paragraphs:
            p_clean = p.strip()
            if not p_clean:
                continue

            if len(current_chunk_text) + len(p_clean) < self.target_chunk_size:
                current_chunk_text += ("\n" + p_clean if current_chunk_text else p_clean)
            else:
                if current_chunk_text:
                    chunks.append(ChunkMetadata(
                        chunk_index=sub_idx,
                        page_number=page_number,
                        rule_number=rule_number,
                        section_title=section_title,
                        content=current_chunk_text.strip(),
                        token_count=len(current_chunk_text.split())
                    ))
                    sub_idx += 1
                    # Overlap: keep tail portion
                    overlap_words = current_chunk_text.split()[-15:]
                    current_chunk_text = " ".join(overlap_words) + "\n" + p_clean
                else:
                    current_chunk_text = p_clean

        if current_chunk_text.strip():
            chunks.append(ChunkMetadata(
                chunk_index=sub_idx,
                page_number=page_number,
                rule_number=rule_number,
                section_title=section_title,
                content=current_chunk_text.strip(),
                token_count=len(current_chunk_text.split())
            ))

        return chunks
