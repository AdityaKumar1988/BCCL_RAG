'use client';

import React from 'react';
import { X, BookOpen, ExternalLink, ShieldCheck, Hash, FileText } from 'lucide-react';
import { Citation } from '../lib/api';

interface CitationDrawerProps {
  isOpen: boolean;
  citation: Citation | null;
  onClose: () => void;
}

export default function CitationDrawer({ isOpen, citation, onClose }: CitationDrawerProps) {
  if (!isOpen || !citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-opacity">
      <div className="w-full max-w-md bg-bccl-surface border-l border-bccl-border h-full shadow-2xl flex flex-col p-6 overflow-y-auto">
        <div className="flex items-center justify-between pb-4 border-b border-bccl-border">
          <div className="flex items-center space-x-2 text-amber-400">
            <BookOpen className="w-5 h-5" />
            <h3 className="font-bold text-base text-white">Source Citation Inspector</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-bccl-muted hover:text-white hover:bg-bccl-card transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="mt-6 space-y-5">
          {/* Document Header */}
          <div className="bg-bccl-card p-4 rounded-xl border border-bccl-border space-y-2">
            <p className="text-xs text-bccl-muted uppercase tracking-wider font-semibold">Official Document</p>
            <h4 className="text-sm font-bold text-white leading-snug">{citation.document_name}</h4>
            <div className="flex flex-wrap gap-2 pt-2 text-xs">
              <span className="px-2.5 py-1 rounded bg-amber-500/10 text-amber-400 font-semibold border border-amber-500/20 flex items-center space-x-1">
                <FileText className="w-3 h-3" />
                <span>Page {citation.page_number}</span>
              </span>
              {citation.rule_number && (
                <span className="px-2.5 py-1 rounded bg-blue-500/10 text-blue-400 font-semibold border border-blue-500/20 flex items-center space-x-1">
                  <Hash className="w-3 h-3" />
                  <span>{citation.rule_number}</span>
                </span>
              )}
              <span className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 font-mono text-[11px] border border-emerald-500/20 flex items-center space-x-1">
                <ShieldCheck className="w-3 h-3" />
                <span>Relevance: {(citation.score * 100).toFixed(1)}%</span>
              </span>
            </div>
          </div>

          {/* Section Breadcrumb */}
          {citation.section_title && (
            <div>
              <p className="text-xs text-bccl-muted uppercase tracking-wider font-semibold mb-1">Section / Chapter</p>
              <p className="text-xs bg-bccl-card p-3 rounded-lg border border-bccl-border text-slate-300">
                {citation.section_title}
              </p>
            </div>
          )}

          {/* Source Text Excerpt */}
          <div>
            <p className="text-xs text-bccl-muted uppercase tracking-wider font-semibold mb-1">Retrieved Document Text</p>
            <div className="bg-bccl-dark p-4 rounded-xl border border-bccl-border text-xs text-slate-200 leading-relaxed font-mono whitespace-pre-wrap">
              {citation.excerpt}
            </div>
          </div>

          {/* Verification Badge */}
          <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 flex items-start space-x-3 text-xs text-emerald-300">
            <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-white">Grounded & Verified</p>
              <p className="text-[11px] text-emerald-400/90 mt-0.5">
                This excerpt is indexed in the BCCL Knowledge Base and verified by the Hybrid Retrieval engine.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
