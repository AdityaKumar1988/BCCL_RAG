import re
from typing import List, Tuple
from backend.app.models.chunk import DocumentChunk
from backend.app.core.config import settings
from backend.app.core.logging import logger

class Reranker:
    """
    Reranks top candidate chunks using domain-specific lexical-semantic matching,
    intent classification, and exact rule bonus.
    """
    def __init__(self):
        self.enabled = settings.ENABLE_RERANKER

    def rerank(self, query: str, candidates: List[Tuple[DocumentChunk, float]]) -> List[Tuple[DocumentChunk, float]]:
        if not self.enabled or not candidates:
            return candidates

        query_lower = query.lower()
        query_words = set(re.findall(r"\w+", query_lower))

        reranked = []
        for chunk, initial_score in candidates:
            boost = 0.0
            content_lower = chunk.content.lower()

            # Rule match boost
            if chunk.rule_number:
                rule_clean = chunk.rule_number.lower()
                if rule_clean in query_lower or any(w in rule_clean for w in query_words if len(w) > 3):
                    boost += 0.35

            # Intent specific boosts
            if "suspension" in query_lower or "suspend" in query_lower:
                if "rule 26" in content_lower or "subsistence allowance" in content_lower or "suspension" in (chunk.rule_number or "").lower():
                    boost += 0.50

            if "major penalties" in query_lower or "major penalty" in query_lower:
                if "major penalties:" in content_lower or "dismissal from service" in content_lower or "compulsory retirement" in content_lower:
                    boost += 0.60
                elif "rule 27" in (chunk.rule_number or "").lower():
                    boost += 0.40

            if "misconduct" in query_lower:
                if "rule 5" in (chunk.rule_number or "").lower() or "theft, fraud" in content_lower:
                    boost += 0.55

            if "appeal" in query_lower or "appellate" in query_lower:
                if "rule 34" in (chunk.rule_number or "").lower() or "period of limitation" in content_lower or "appellate authority" in content_lower:
                    boost += 0.60

            # Penalize irrelevant matches if core query terms are missing
            core_words = [w for w in query_words if w not in ["what", "when", "where", "which", "about", "rules", "tell", "explain", "does", "have", "can", "an", "the", "for", "is", "in", "of"]]
            matched_core = [w for w in core_words if w in content_lower]
            match_ratio = len(matched_core) / max(len(core_words), 1)

            final_score = (initial_score * 0.4) + (boost * 0.4) + (match_ratio * 0.2)
            reranked.append((chunk, final_score))

        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked
