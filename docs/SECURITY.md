# ENTERPRISE SECURITY & PROMPT INJECTION DEFENSE SPECIFICATION

## 1. Security Architecture Summary

The system adheres to enterprise cybersecurity and responsible AI guidelines:

1. **Authentication & RBAC**:
   - Passwords hashed using Bcrypt with salted rounds.
   - Stateless HS256 JWT tokens with configurable TTL.
   - Role-Based Access Control (`admin`, `user`, `auditor`) guarding sensitive endpoints.
2. **File Ingestion Security**:
   - MIME validation and magic-byte checks.
   - Strict 50MB file size ceiling per PDF.
   - Sanitization of uploaded file names (`uuid.uuid4().hex[:8]_filename.pdf`) preventing path traversal.
3. **Prompt Injection & Boundary Defense**:
   - User inputs and retrieved document chunks are strictly isolated within `<evidence_context>` XML boundary tags.
   - The system prompt explicitly commands LLMs to treat all text inside `<evidence_context>` as untrusted reference data and never follow instructions contained inside documents.
4. **Audit Trail**:
   - All document uploads, re-indexings, deletions, user logins, and chat queries are recorded with user IDs and timestamps in the `audit_logs` table.
5. **Data Protection & Grounding**:
   - Zero hardcoded secrets or API keys in the source code.
   - All environment variables managed via `.env`.
