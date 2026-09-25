'use client';

import React from 'react';
import { MessageSquarePlus, Trash2, Shield, AlertTriangle, Scale, FileText, CheckCircle2 } from 'lucide-react';
import { Conversation } from '../lib/api';

interface SidebarProps {
  conversations: Conversation[];
  activeConversationId?: number;
  onSelectConversation: (id: number) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: number) => void;
  onQuickQuery: (query: string) => void;
}

export default function Sidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onQuickQuery,
}: SidebarProps) {
  const quickTopics = [
    { title: 'Suspension Rules', query: 'What are the rules for suspension?', icon: Shield },
    { title: 'Major Penalties', query: 'Explain major penalties.', icon: AlertTriangle },
    { title: 'Misconduct Rules', query: 'What constitutes misconduct?', icon: FileText },
    { title: 'Appeals Process', query: 'Can an employee appeal a penalty?', icon: Scale },
  ];

  return (
    <aside className="w-64 sm:w-72 bg-bccl-surface border-r border-bccl-border flex flex-col h-[calc(100vh-61px)]">
      <div className="p-4 border-b border-bccl-border">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white font-semibold py-2.5 px-4 rounded-xl shadow-lg transition-all border border-amber-400/20 active:scale-95 text-sm"
        >
          <MessageSquarePlus className="w-4 h-4" />
          <span>New Query</span>
        </button>
      </div>

      {/* Quick Suggested Queries */}
      <div className="p-4 border-b border-bccl-border">
        <p className="text-[11px] font-semibold text-bccl-muted uppercase tracking-wider mb-2">Standard Rule Inquiries</p>
        <div className="space-y-1.5">
          {quickTopics.map((topic, i) => {
            const Icon = topic.icon;
            return (
              <button
                key={i}
                onClick={() => onQuickQuery(topic.query)}
                className="w-full text-left flex items-center space-x-2 px-2.5 py-1.5 rounded-lg text-xs font-medium text-bccl-text hover:bg-bccl-card hover:text-amber-400 transition-colors border border-transparent hover:border-bccl-border"
              >
                <Icon className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                <span className="truncate">{topic.title}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Conversation History */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <p className="text-[11px] font-semibold text-bccl-muted uppercase tracking-wider px-2 mb-2">Recent Chats</p>
        {conversations.length === 0 ? (
          <div className="text-center py-8 text-bccl-muted text-xs">
            No previous conversations.
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = conv.id === activeConversationId;
            return (
              <div
                key={conv.id}
                onClick={() => onSelectConversation(conv.id)}
                className={`group flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium cursor-pointer transition-all border ${
                  isActive
                    ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                    : 'text-bccl-text hover:bg-bccl-card border-transparent'
                }`}
              >
                <span className="truncate flex-1 pr-2">{conv.title || 'Conversation'}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 text-bccl-muted transition-opacity"
                  title="Delete chat"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-bccl-border bg-bccl-dark/40 text-[11px] text-bccl-muted">
        <div className="flex items-center space-x-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>Grounded in CDA Rules 1978</span>
        </div>
      </div>
    </aside>
  );
}
