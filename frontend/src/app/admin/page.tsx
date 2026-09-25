'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  UploadCloud,
  FileText,
  Trash2,
  RotateCw,
  BarChart3,
  Users,
  MessageSquare,
  ShieldCheck,
  Clock,
  ThumbsUp,
  ThumbsDown,
  AlertCircle,
  CheckCircle2,
  Layers,
  Sparkles
} from 'lucide-react';
import DocumentUploadModal from '../../components/DocumentUploadModal';
import {
  getDocumentsApi,
  getAnalyticsApi,
  deleteDocumentApi,
  reindexDocumentApi,
  DocumentItem,
  AnalyticsData
} from '../../lib/api';
import { getStoredUser } from '../../lib/auth';

export default function AdminPage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  useEffect(() => {
    const user = getStoredUser();
    if (!user || user.role !== 'admin') {
      router.push('/');
      return;
    }
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [docs, stats] = await Promise.all([getDocumentsApi(), getAnalyticsApi()]);
      setDocuments(docs);
      setAnalytics(stats);
    } catch (err) {
      console.error('Failed to load admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReindex = async (docId: number) => {
    try {
      await reindexDocumentApi(docId);
      setActionMessage(`Document #${docId} re-indexing queued successfully!`);
      setTimeout(() => {
        setActionMessage(null);
        loadData();
      }, 1500);
    } catch (err) {
      alert('Failed to trigger re-index');
    }
  };

  const handleDelete = async (docId: number) => {
    if (!confirm('Are you sure you want to delete this document and all its indexed chunks?')) return;
    try {
      await deleteDocumentApi(docId);
      setActionMessage(`Document #${docId} deleted.`);
      setTimeout(() => {
        setActionMessage(null);
        loadData();
      }, 1200);
    } catch (err) {
      alert('Failed to delete document');
    }
  };

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-61px)] bg-bccl-dark p-6 overflow-y-auto">
      <div className="max-w-6xl w-full mx-auto space-y-8">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-bccl-border pb-6">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-3">
              <BarChart3 className="w-7 h-7 text-amber-500" />
              <span>BCCL System Administration & Analytics</span>
            </h1>
            <p className="text-xs text-bccl-muted mt-1">
              Document ingestion lifecycle, OCR pipeline management, vector indexing, and usage observability.
            </p>
          </div>

          <button
            onClick={() => setUploadModalOpen(true)}
            className="flex items-center space-x-2 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white font-semibold py-2.5 px-5 rounded-xl shadow-lg transition-all border border-amber-400/20 active:scale-95 text-xs"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload New PDF</span>
          </button>
        </div>

        {actionMessage && (
          <div className="p-3 bg-emerald-950/50 border border-emerald-500/40 rounded-xl flex items-center space-x-2 text-xs text-emerald-300">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{actionMessage}</span>
          </div>
        )}

        {/* Analytics KPIs Grid */}
        {analytics && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="bg-bccl-surface border border-bccl-border p-4 rounded-2xl">
              <p className="text-[11px] font-semibold text-bccl-muted uppercase tracking-wider">Documents</p>
              <p className="text-2xl font-bold text-white mt-1">{analytics.total_documents}</p>
              <p className="text-[10px] text-amber-400 mt-1">{analytics.scanned_docs_count} OCR Scanned</p>
            </div>

            <div className="bg-bccl-surface border border-bccl-border p-4 rounded-2xl">
              <p className="text-[11px] font-semibold text-bccl-muted uppercase tracking-wider">Total Chunks</p>
              <p className="text-2xl font-bold text-white mt-1">{analytics.total_chunks}</p>
              <p className="text-[10px] text-blue-400 mt-1">Structure-Aware</p>
            </div>

            <div className="bg-bccl-surface border border-bccl-border p-4 rounded-2xl">
              <p className="text-[11px] font-semibold text-bccl-muted uppercase tracking-wider">Total Queries</p>
              <p className="text-2xl font-bold text-white mt-1">{analytics.total_queries}</p>
              <p className="text-[10px] text-emerald-400 mt-1">{analytics.total_conversations} Sessions</p>
            </div>

            <div className="bg-bccl-surface border border-bccl-border p-4 rounded-2xl">
              <p className="text-[11px] font-semibold text-bccl-muted uppercase tracking-wider">Avg Latency</p>
              <p className="text-2xl font-bold text-white mt-1">{analytics.avg_latency_ms}ms</p>
              <p className="text-[10px] text-purple-400 mt-1">Hybrid Retrieval</p>
            </div>

            <div className="bg-bccl-surface border border-bccl-border p-4 rounded-2xl">
              <p className="text-[11px] font-semibold text-bccl-muted uppercase tracking-wider">Positive Feedback</p>
              <p className="text-2xl font-bold text-emerald-400 mt-1">{analytics.positive_feedback_count}</p>
              <p className="text-[10px] text-bccl-muted mt-1">Grounding verified</p>
            </div>

            <div className="bg-bccl-surface border border-bccl-border p-4 rounded-2xl">
              <p className="text-[11px] font-semibold text-bccl-muted uppercase tracking-wider">Registered Users</p>
              <p className="text-2xl font-bold text-white mt-1">{analytics.total_users}</p>
              <p className="text-[10px] text-amber-400 mt-1">RBAC Enabled</p>
            </div>
          </div>
        )}

        {/* Documents Table */}
        <div className="bg-bccl-surface border border-bccl-border rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <FileText className="w-5 h-5 text-amber-500" />
              <span>Knowledge Base Documents</span>
            </h3>
            <button
              onClick={loadData}
              className="p-2 text-bccl-muted hover:text-white hover:bg-bccl-card rounded-lg transition-colors"
              title="Refresh"
            >
              <RotateCw className="w-4 h-4" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-bccl-card text-bccl-muted uppercase tracking-wider border-b border-bccl-border">
                <tr>
                  <th className="py-3 px-4">Document Title</th>
                  <th className="py-3 px-4">File Name</th>
                  <th className="py-3 px-4">Pages</th>
                  <th className="py-3 px-4">Chunks</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-bccl-border/50 text-slate-300 font-medium">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-bccl-card/50 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-white">{doc.title}</td>
                    <td className="py-3.5 px-4 font-mono text-bccl-muted">{doc.filename}</td>
                    <td className="py-3.5 px-4">{doc.total_pages}</td>
                    <td className="py-3.5 px-4 font-mono text-amber-400">{doc.chunks_count}</td>
                    <td className="py-3.5 px-4">
                      {doc.is_scanned ? (
                        <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 text-[10px] font-semibold">
                          OCR Scanned
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-semibold">
                          Digital PDF
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold text-[11px] flex items-center space-x-1 w-fit">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>{doc.status}</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => handleReindex(doc.id)}
                        className="p-1.5 hover:text-amber-400 text-bccl-muted hover:bg-bccl-card rounded-lg transition-colors"
                        title="Re-Index Document"
                      >
                        <RotateCw className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="p-1.5 hover:text-red-400 text-bccl-muted hover:bg-red-500/10 rounded-lg transition-colors"
                        title="Delete Document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onSuccess={loadData}
      />
    </div>
  );
}
