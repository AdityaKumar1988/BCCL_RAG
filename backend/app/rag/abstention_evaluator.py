import re
from typing import List, Tuple
from backend.app.models.chunk import DocumentChunk
from backend.app.core.config import settings
from backend.app.core.logging import logger

class AbstentionEvaluator:
    """
    Evaluates evidence sufficiency, query-document semantic alignment, and retrieval confidence.
    Enforces strict anti-hallucination policy by triggering abstention when evidence is inadequate.
    """
    ABSTENTION_RESPONSE = "I could not find sufficient information about this in the available BCCL documents."

    def __init__(self, threshold: float = None):
        self.threshold = threshold or settings.ABSTENTION_THRESHOLD

    def evaluate(self, query: str, retrieved_chunks: List[Tuple[DocumentChunk, float]]) -> Tuple[bool, str]:
        """
        Returns (should_abstain: bool, reason: str)
        """
        if not retrieved_chunks:
            logger.info("Abstention: Zero retrieved chunks.")
            return True, "No relevant document chunks found."

        top_score = retrieved_chunks[0][1]
        
        # Stop words and ubiquitous organizational boilerplate words that do not indicate topic match
        stop_words = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "can", "could", "should", "would", "may", "might", "must",
            "a", "an", "the", "and", "or", "but", "if", "for", "with", "about", "against",
            "between", "into", "through", "during", "before", "after", "above", "below",
            "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "all", "any", "both", "each", "few",
            "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same",
            "so", "than", "too", "very", "s", "t", "just", "don", "shouldn", "now", "tell", "me",
            "explain", "rules", "rule", "policy", "provisions", "bccl", "cil", "bharat", "coking",
            "coal", "limited", "company", "employee", "employees", "apply", "officer", "department"
        }
        
        query_tokens = [w for w in re.findall(r"[a-z]+", query.lower()) if len(w) > 2 and w not in stop_words]
        
        # Look at top 3 chunks content (excluding header words)
        top_chunks_text = " ".join([f"{c[0].rule_number or ''} {c[0].section_title or ''} {c[0].content}".lower() for c in retrieved_chunks[:3]])

        # If significant query topic tokens exist, ensure topic keywords actually appear in the chunk content
        if query_tokens:
            matched = [t for t in query_tokens if t in top_chunks_text]
            match_ratio = len(matched) / len(query_tokens)
            
            # If fewer than 50% of the topical words appear in the retrieved text, abstain!
            if match_ratio < 0.50:
                logger.info(f"Abstention: Only {len(matched)} of {len(query_tokens)} query topic tokens {query_tokens} matched in evidence.")
                return True, f"Insufficient topical grounding ({match_ratio:.2%})."

        if top_score < self.threshold:
            logger.info(f"Abstention: Top retrieval score {top_score:.3f} < threshold {self.threshold:.3f}.")
            return True, "Low retrieval confidence score."

        return False, "Sufficient evidence found."
