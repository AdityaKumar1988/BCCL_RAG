'use client';

import React, { useState } from 'react';
import { X, ThumbsUp, ThumbsDown, MessageSquare, Check } from 'lucide-react';
import { submitFeedbackApi } from '../lib/api';

interface FeedbackModalProps {
  isOpen: boolean;
  messageId: number | null;
  initialRating: number;
  onClose: () => void;
  onSuccess: () => void;
}

export default function FeedbackModal({ isOpen, messageId, initialRating, onClose, onSuccess }: FeedbackModalProps) {
  const [rating, setRating] = useState<number>(initialRating);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen || !messageId) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await submitFeedbackApi(messageId, rating, comment);
      setSubmitted(true);
      setTimeout(() => {
        setSubmitted(false);
        onSuccess();
        onClose();
      }, 1200);
    } catch (err) {
      alert('Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-bccl-surface border border-bccl-border rounded-2xl shadow-2xl p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-lg text-bccl-muted hover:text-white hover:bg-bccl-card transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <h3 className="text-base font-bold text-white mb-2">Response Quality Feedback</h3>
        <p className="text-xs text-bccl-muted mb-4">
          Help us refine the BCCL Knowledge Retrieval System. Your feedback directly trains our retrieval calibration.
        </p>

        {submitted ? (
          <div className="py-8 flex flex-col items-center justify-center space-y-2 text-emerald-400">
            <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center border border-emerald-500/30">
              <Check className="w-6 h-6" />
            </div>
            <p className="font-semibold text-sm">Feedback Recorded!</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex justify-center space-x-4 py-2">
              <button
                type="button"
                onClick={() => setRating(1)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-xl border text-sm font-semibold transition-all ${
                  rating === 1
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-lg'
                    : 'bg-bccl-card text-bccl-muted border-bccl-border hover:text-white'
                }`}
              >
                <ThumbsUp className="w-4 h-4" />
                <span>Accurate</span>
              </button>

              <button
                type="button"
                onClick={() => setRating(-1)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-xl border text-sm font-semibold transition-all ${
                  rating === -1
                    ? 'bg-red-500/20 text-red-300 border-red-500/40 shadow-lg'
                    : 'bg-bccl-card text-bccl-muted border-bccl-border hover:text-white'
                }`}
              >
                <ThumbsDown className="w-4 h-4" />
                <span>Needs Improvement</span>
              </button>
            </div>

            <div>
              <label className="block text-xs font-semibold text-bccl-muted uppercase tracking-wider mb-1">
                Optional Comments
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Mention if citations were accurate, rule number was missing, or text was unclear..."
                className="w-full h-24 bg-bccl-dark border border-bccl-border rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
              />
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
                disabled={submitting}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white transition-colors disabled:opacity-50"
              >
                {submitting ? 'Submitting...' : 'Submit Feedback'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
