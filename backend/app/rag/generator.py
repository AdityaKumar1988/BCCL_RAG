import time
from typing import List, Tuple, Optional, Generator
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.models.chunk import DocumentChunk
from backend.app.models.message import Message
from backend.app.schemas.chat import CitationItem
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.rag.query_processor import QueryProcessor
from backend.app.rag.abstention_evaluator import AbstentionEvaluator
from backend.app.rag.context_builder import ContextBuilder
from backend.app.rag.citation_engine import CitationEngine
from backend.app.providers.llm_provider import LLMProviderFactory, BaseLLMProvider

class RAGGenerator:
    def __init__(self, db: Session, llm_provider: Optional[BaseLLMProvider] = None):
        self.db = db
        self.retriever = HybridRetriever(db)
        self.query_processor = QueryProcessor()
        self.abstention_evaluator = AbstentionEvaluator()
        self.llm_provider = llm_provider or LLMProviderFactory.get_provider()

    def generate_answer(
        self,
        query: str,
        history: List[Message] = [],
        document_id: Optional[int] = None,
        knowledge_base: Optional[str] = None
    ) -> Tuple[str, List[CitationItem], bool, float, List[Tuple[DocumentChunk, float]]]:
        start_time = time.time()

        # Step 1: Query understanding & rewriting
        processed_query = self.query_processor.rewrite_conversational_query(query, history)
        logger.info(f"Original Query: '{query}' -> Processed Query: '{processed_query}' (KB: {knowledge_base})")

        # Step 2: Hybrid Retrieval (Dense + BM25 + Rerank)
        retrieved_chunks = self.retriever.retrieve(
            processed_query,
            document_id=document_id,
            knowledge_base=knowledge_base
        )

        # Step 3: Evidence Evaluation & Abstention Check
        should_abstain, reason = self.abstention_evaluator.evaluate(processed_query, retrieved_chunks)
        
        if should_abstain:
            latency_ms = (time.time() - start_time) * 1000.0
            return (
                AbstentionEvaluator.ABSTENTION_RESPONSE,
                [],
                True,
                latency_ms,
                retrieved_chunks
            )

        # Step 4: Build Prompt & Context
        history_text = "\n".join([f"{m.sender.capitalize()}: {m.content[:200]}" for m in history[-4:]])
        context = ContextBuilder.build_grounded_context(retrieved_chunks)
        rag_prompt = ContextBuilder.build_rag_prompt(
            user_query=query,
            evidence_context=context,
            history_context=history_text
        )

        # Step 5: LLM Generation
        raw_answer = self.llm_provider.generate_response(rag_prompt)

        # Step 6: Check if LLM itself signaled abstention
        is_abstention = (
            "could not find sufficient information" in raw_answer.lower()
            or "information is not available" in raw_answer.lower()
        )

        # Step 7: Build Citations
        citations = [] if is_abstention else CitationEngine.build_citations(retrieved_chunks[:3])
        latency_ms = (time.time() - start_time) * 1000.0

        return raw_answer, citations, is_abstention, latency_ms, retrieved_chunks

    def generate_stream(
        self,
        query: str,
        history: List[Message] = [],
        document_id: Optional[int] = None,
        knowledge_base: Optional[str] = None
    ) -> Generator[str, None, None]:
        processed_query = self.query_processor.rewrite_conversational_query(query, history)
        retrieved_chunks = self.retriever.retrieve(
            processed_query,
            document_id=document_id,
            knowledge_base=knowledge_base
        )
        should_abstain, _ = self.abstention_evaluator.evaluate(processed_query, retrieved_chunks)

        if should_abstain:
            yield AbstentionEvaluator.ABSTENTION_RESPONSE
            return

        history_text = "\n".join([f"{m.sender.capitalize()}: {m.content[:200]}" for m in history[-4:]])
        context = ContextBuilder.build_grounded_context(retrieved_chunks)
        rag_prompt = ContextBuilder.build_rag_prompt(
            user_query=query,
            evidence_context=context,
            history_context=history_text
        )

        for chunk in self.llm_provider.generate_stream(rag_prompt):
            yield chunk
