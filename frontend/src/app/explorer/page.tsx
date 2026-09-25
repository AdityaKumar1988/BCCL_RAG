'use client';

import React, { useState, useEffect } from 'react';
import { Search, BookOpen, FileText, Hash, Eye, Sparkles, Filter, ShieldCheck } from 'lucide-react';
import CitationDrawer from '../../components/CitationDrawer';
import { getDocumentsApi, searchKnowledgeApi, getDocumentChunksApi, DocumentItem, ChunkItem, Citation } from '../../lib/api';

export default function ExplorerPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');
  const [chunks, setChunks] = useState<ChunkItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    loadDocs();
  }, []);

  const loadDocs = async () => {
    try {
      const docs = await getDocumentsApi();
      setDocuments(docs);
      if (docs.length > 0) {
        setSelectedDocId(docs[0].id);
        loadChunks(docs[0].id);
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const loadChunks = async (docId: number) => {
    setLoading(true);
    try {
      const list = await getDocumentChunksApi(docId);
      setChunks(list);
    } catch (err) {
      console.error('Failed to load chunks:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      if (selectedDocId) loadChunks(selectedDocId);
      return;
    }
    setLoading(true);
    try {
      const results = await searchKnowledgeApi(searchQuery, selectedDocId);
      setChunks(results);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInspectChunk = (c: ChunkItem) => {
    const doc = documents.find((d) => d.id === c.document_id);
    setSelectedCitation({
      chunk_id: c.id,
      document_id: c.document_id,
      document_name: doc?.title || 'BCCL Document',
      page_number: c.page_number,
      rule_number: c.rule_number,
      section_title: c.section_title,
      excerpt: c.content,
      score: c.score || 1.0
    });
    setDrawerOpen(true);
  };

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-61px)] bg-bccl-dark p-6 overflow-y-auto">
      <div className="max-w-6xl w-full mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-bccl-border pb-6">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-3">
              <BookOpen className="w-7 h-7 text-amber-500" />
              <span>BCCL Knowledge Explorer</span>
            </h1>
            <p className="text-xs text-bccl-muted mt-1">
              Search, browse, and inspect indexed rules, legal clauses, and chunk structures in the knowledge repository.
            </p>
          </div>

          {/* Document Filter Selector */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-amber-500" />
            <select
              value={selectedDocId || ''}
              onChange={(e) => {
                const id = Number(e.target.value);
                setSelectedDocId(id);
                loadChunks(id);
              }}
              className="bg-bccl-surface border border-bccl-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.title} ({d.chunks_count} chunks)
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search across all indexed rules (e.g. 'Rule 26', 'suspension', 'appeal', 'theft')..."
            className="w-full bg-bccl-surface border border-bccl-border rounded-2xl py-3.5 pl-11 pr-28 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 shadow-lg"
          />
          <Search className="w-4 h-4 text-slate-400 absolute left-4 top-4" />
          <button
            type="submit"
            className="absolute right-2.5 top-2 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs rounded-xl transition-colors"
          >
            Search Rules
          </button>
        </form>

        {/* Chunks List */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-semibold text-bccl-muted uppercase tracking-wider">
              {searchQuery ? `Search Results (${chunks.length})` : `Indexed Chunks (${chunks.length})`}
            </p>
            <span className="text-xs text-amber-400 font-medium">Hybrid BM25 + Dense Semantic Match</span>
          </div>

          {loading ? (
            <div className="py-16 text-center text-xs text-bccl-muted space-y-2">
              <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p>Scanning knowledge repository...</p>
            </div>
          ) : chunks.length === 0 ? (
            <div className="p-12 text-center bg-bccl-surface border border-bccl-border rounded-2xl text-xs text-bccl-muted">
              No matching chunks found for your search query.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {chunks.map((c) => (
                <div
                  key={c.id}
                  className="bg-bccl-surface border border-bccl-border hover:border-amber-500/50 rounded-2xl p-5 shadow-lg flex flex-col justify-between transition-all group"
                >
                  <div className="space-y-3">
                    {/* Tags Header */}
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center space-x-2">
                        {c.rule_number ? (
                          <span className="px-2.5 py-0.5 rounded bg-amber-500/10 text-amber-400 font-bold text-xs border border-amber-500/20">
                            {c.rule_number}
                          </span>
                        ) : (
                          <span className="px-2.5 py-0.5 rounded bg-bccl-card text-slate-400 text-xs border border-bccl-border">
                            Section Clause
                          </span>
                        )}
                        <span className="text-[11px] text-bccl-muted">Page {c.page_number}</span>
                      </div>

                      {c.score !== undefined && (
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/20">
                          Score: {(c.score * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>

                    {/* Section Title */}
                    {c.section_title && (
                      <p className="text-xs font-semibold text-slate-300 line-clamp-1">{c.section_title}</p>
                    )}

                    {/* Content Preview */}
                    <p className="text-xs text-slate-400 font-mono leading-relaxed line-clamp-4 bg-bccl-dark/60 p-3 rounded-xl border border-bccl-border/60">
                      {c.content}
                    </p>
                  </div>

                  {/* Footer Action */}
                  <div className="pt-4 mt-2 border-t border-bccl-border/50 flex items-center justify-between">
                    <span className="text-[10px] text-bccl-muted">Chunk #{c.chunk_index} ({c.token_count} words)</span>
                    <button
                      onClick={() => handleInspectChunk(c)}
                      className="flex items-center space-x-1.5 text-xs font-semibold text-amber-400 hover:text-amber-300 transition-colors"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Inspect Context</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Citation Drawer */}
      <CitationDrawer
        isOpen={drawerOpen}
        citation={selectedCitation}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  );
}
