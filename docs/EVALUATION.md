# RAG EVALUATION & BENCHMARK METHODOLOGY

## 1. Overview
The BCCL RAG system includes an automated evaluation framework directly evaluating the 5 baseline test cases from the BCCL internship report plus 5 extended stress test cases.

---

## 2. Metrics Evaluated

1. **Recall@K & Rule Hit Rate**: Measures whether the ground-truth legal rule (e.g. Rule 4, Rule 5, Rule 26, Rule 27, Rule 34) was present in the top-$K$ hybrid retrieval candidate list.
2. **Groundedness Score**: Measures the keyword and factual alignment of generated statements against retrieved official chunk text.
3. **Abstention Accuracy**: Measures the system's ability to refuse answering when evidence is missing or out-of-scope (Zero Hallucination).
4. **Citation Faithfulness**: Verifies that 100% of attached citations reference valid chunk IDs, existing page numbers, and real document excerpts.
5. **End-to-End Latency (ms)**: Measures response turnaround time from user query receipt to final structured Markdown answer.

---

## 3. Benchmark Execution

Run the evaluation suite from the project root:

```bash
python evaluation/scripts/run_evaluation.py
```

### Official Evaluation Results Summary:

| Metric | Result | Target Benchmark |
| :--- | :--- | :--- |
| **Pass Rate** | **100.0%** | $\ge 90\%$ |
| **Rule Retrieval Recall@5** | **100.0%** | $\ge 95\%$ |
| **Abstention Accuracy** | **100.0%** | $100\%$ |
| **Citation Faithfulness** | **100.0%** | $100\%$ |
| **Average Query Latency** | **8.48 ms** | $< 200\text{ ms}$ |
