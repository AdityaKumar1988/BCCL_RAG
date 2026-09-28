from typing import List, Tuple
from backend.app.models.chunk import DocumentChunk
from backend.app.schemas.chat import CitationItem

class CitationEngine:
    """
    Builds authentic, verifiable citation items directly tied to actual retrieved chunks.
    """
    @staticmethod
    def build_citations(retrieved_chunks: List[Tuple[DocumentChunk, float]]) -> List[CitationItem]:
        citations: List[CitationItem] = []
        seen_chunks = set()

        for chunk, score in retrieved_chunks:
            if chunk.id in seen_chunks:
                continue
            seen_chunks.add(chunk.id)

            doc_title = chunk.document.title if chunk.document else "BCCL Official Document"
            
            # Excerpt first 200 chars
            excerpt = chunk.content.strip().replace("\n", " ")
            if len(excerpt) > 200:
                excerpt = excerpt[:197] + "..."

            citations.append(CitationItem(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_name=doc_title,
                knowledge_base=getattr(chunk, "knowledge_base", None) or (chunk.document.knowledge_base if chunk.document else "BCCL_Rules"),
                page_number=chunk.page_number,
                rule_number=chunk.rule_number,
                section_title=chunk.section_title,
                excerpt=excerpt,
                score=round(score, 4)
            ))

        return citations
