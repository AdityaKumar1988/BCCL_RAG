'use client';

import React, { useState } from 'react';
import { X, UploadCloud, FileText, AlertCircle, CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import { uploadDocumentApi } from '../lib/api';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function DocumentUploadModal({ isOpen, onClose, onSuccess }: DocumentUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successStatus, setSuccessStatus] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (!selected.name.toLowerCase().endsWith('.pdf')) {
        setError('Only official PDF files (.pdf) are supported.');
        return;
      }
      setFile(selected);
      setError(null);
      if (!title) {
        setTitle(selected.name.replace(/\.pdf$/i, '').replace(/_/g, ' '));
      }
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a PDF document to upload.');
      return;
    }

    setUploading(true);
    setError(null);
    try {
      const res = await uploadDocumentApi(file, title);
      setSuccessStatus(`Job Created (${res.status}). Ingestion pipeline triggered in background!`);
      setTimeout(() => {
        setSuccessStatus(null);
        setFile(null);
        setTitle('');
        onSuccess();
        onClose();
      }, 1800);
    } catch (err: any) {
      setError(err.message || 'Failed to upload document.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-bccl-surface border border-bccl-border rounded-2xl shadow-2xl p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-lg text-bccl-muted hover:text-white hover:bg-bccl-card transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-2">
          <div className="w-9 h-9 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center border border-amber-500/30">
            <UploadCloud className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Upload BCCL Official Document</h3>
            <p className="text-xs text-bccl-muted">PDF Ingestion with OCR & Structure-Aware Chunking</p>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-950/50 border border-red-500/40 rounded-xl flex items-center space-x-2 text-xs text-red-300">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successStatus ? (
          <div className="py-8 flex flex-col items-center justify-center space-y-2 text-emerald-400">
            <CheckCircle2 className="w-10 h-10 animate-bounce" />
            <p className="font-semibold text-sm">{successStatus}</p>
          </div>
        ) : (
          <form onSubmit={handleUpload} className="mt-5 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-bccl-muted uppercase tracking-wider mb-1">
                Document Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. BCCL CDA Rules 1978 (Amended 2026)"
                className="w-full bg-bccl-dark border border-bccl-border rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-bccl-muted uppercase tracking-wider mb-1">
                PDF File (.pdf)
              </label>
              <label className="flex flex-col items-center justify-center border-2 border-dashed border-bccl-border hover:border-amber-500/60 rounded-xl p-6 bg-bccl-dark/60 cursor-pointer transition-colors group">
                <FileText className="w-8 h-8 text-bccl-muted group-hover:text-amber-400 mb-2 transition-colors" />
                <span className="text-xs text-slate-300 font-medium">
                  {file ? file.name : 'Click to select or drag & drop PDF document'}
                </span>
                <span className="text-[10px] text-bccl-muted mt-1">
                  Supports digital PDFs and scanned image copies (OCR enabled)
                </span>
                <input type="file" accept=".pdf" onChange={handleFileChange} className="hidden" />
              </label>
            </div>

            <div className="bg-bccl-card p-3 rounded-xl border border-bccl-border text-[11px] text-slate-300 space-y-1">
              <div className="flex items-center space-x-1.5 text-amber-400 font-semibold">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Automatic Pipeline Actions:</span>
              </div>
              <p>• Scanned pages are automatically detected and processed with Tesseract OCR (300 DPI).</p>
              <p>• Legal rule numbers & chapter boundaries are extracted for precision retrieval.</p>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-medium text-bccl-muted hover:text-white hover:bg-bccl-card transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={uploading || !file}
                className="flex items-center space-x-2 px-5 py-2 rounded-xl text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white transition-colors disabled:opacity-50"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Ingesting Document...</span>
                  </>
                ) : (
                  <span>Start Ingestion</span>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
