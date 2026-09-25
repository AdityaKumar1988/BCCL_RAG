import re
from typing import List, Optional
from backend.app.models.message import Message

class QueryProcessor:
    """
    Processes natural language queries, expands domain-specific acronyms,
    and performs conversational query rewriting based on conversation history.
    """
    ACRONYM_MAP = {
        r"\bcda\b": "Conduct, Discipline and Appeal (CDA)",
        r"\bcil\b": "Coal India Limited (CIL)",
        r"\bbccl\b": "Bharat Coking Coal Limited (BCCL)",
        r"\bda\b": "Disciplinary Authority",
        r"\baa\b": "Appellate Authority",
        r"\bio\b": "Inquiring Authority (Inquiry Officer)",
        r"\bsop\b": "Standard Operating Procedure",
    }

    def expand_query(self, query: str) -> str:
        expanded = query.strip()
        for pattern, replacement in self.ACRONYM_MAP.items():
            expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
        return expanded

    def rewrite_conversational_query(self, current_query: str, history: List[Message]) -> str:
        """
        If the current query is an ambiguous follow-up (e.g. 'what about suspension?', 'and the appeals?'),
        leverages recent assistant/user messages to reformulate a standalone searchable query.
        """
        trimmed = current_query.strip()
        trimmed_lower = trimmed.lower()

        # Follow-up indicators
        is_follow_up = any(trimmed_lower.startswith(p) for p in [
            "what about", "how about", "and", "can they", "is there", "what if", "tell me more", "explain that"
        ]) or len(trimmed.split()) <= 3

        if not is_follow_up or not history:
            return self.expand_query(current_query)

        # Look at last user query and last assistant answer
        last_user_msg = next((m.content for m in reversed(history) if m.sender == "user"), "")
        
        # Merge context
        context_anchor = ""
        if "cda" in last_user_msg.lower() or "rule" in last_user_msg.lower():
            context_anchor = "in BCCL CDA Rules"
        elif "penalt" in last_user_msg.lower():
            context_anchor = "regarding penalties and disciplinary action in BCCL"
        elif "conduct" in last_user_msg.lower():
            context_anchor = "under BCCL Employee Conduct Rules"

        rewritten = f"{trimmed} {context_anchor}".strip()
        return self.expand_query(rewritten)
