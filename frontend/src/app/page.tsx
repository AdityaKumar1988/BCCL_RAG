'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Send,
  Sparkles,
  Bot,
  User as UserIcon,
  BookOpen,
  ThumbsUp,
  ThumbsDown,
  Copy,
  Check,
  Shield,
  Clock,
  AlertTriangle,
  RotateCw,
  Search
} from 'lucide-react';
import Sidebar from '../components/Sidebar';
import CitationDrawer from '../components/CitationDrawer';
import FeedbackModal from '../components/FeedbackModal';
import {
  getConversationsApi,
  getConversationApi,
  deleteConversationApi,
  sendChatMessageApi,
  Conversation,
  Message,
  Citation
} from '../lib/api';
import { isAuthenticated } from '../lib/auth';

export default function AssistantPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | undefined>(undefined);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [citationDrawerOpen, setCitationDrawerOpen] = useState(false);
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [feedbackTargetMessageId, setFeedbackTargetMessageId] = useState<number | null>(null);
  const [feedbackInitialRating, setFeedbackInitialRating] = useState<number>(1);
  const [copiedMessageId, setCopiedMessageId] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }
    loadConversations();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const loadConversations = async () => {
    try {
      const list = await getConversationsApi();
      setConversations(list);
      if (list.length > 0 && !activeConversationId) {
        loadConversationDetails(list[0].id);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  const loadConversationDetails = async (id: number) => {
    try {
      setActiveConversationId(id);
      const conv = await getConversationApi(id);
      setMessages(conv.messages || []);
    } catch (err) {
      console.error('Failed to load conversation details:', err);
    }
  };

  const handleNewConversation = () => {
    setActiveConversationId(undefined);
    setMessages([]);
  };

  const handleDeleteConversation = async (id: number) => {
    try {
      await deleteConversationApi(id);
      const updated = conversations.filter((c) => c.id !== id);
      setConversations(updated);
      if (activeConversationId === id) {
        if (updated.length > 0) {
          loadConversationDetails(updated[0].id);
        } else {
          handleNewConversation();
        }
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim() || loading) return;

    const userMsgTemp: Message = {
      id: Date.now(),
      conversation_id: activeConversationId || 0,
      sender: 'user',
      content: textToSend,
      citations: [],
      latency_ms: 0,
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, userMsgTemp]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await sendChatMessageApi(textToSend, activeConversationId);
      
      const asstMsg: Message = {
        id: res.message_id,
        conversation_id: res.conversation_id,
        sender: 'assistant',
        content: res.answer,
        citations: res.citations || [],
        latency_ms: res.latency_ms,
        created_at: new Date().toISOString()
      };

      setMessages((prev) => [...prev, asstMsg]);

      if (!activeConversationId) {
        setActiveConversationId(res.conversation_id);
        loadConversations();
      }
    } catch (err: any) {
      const errorMsg: Message = {
        id: Date.now() + 1,
        conversation_id: activeConversationId || 0,
        sender: 'assistant',
        content: `Error: ${err.message || 'Failed to retrieve grounded response. Please try again.'}`,
        citations: [],
        latency_ms: 0,
        created_at: new Date().toISOString()
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleCitationClick = (citation: Citation) => {
    setSelectedCitation(citation);
    setCitationDrawerOpen(true);
  };

  const handleOpenFeedback = (messageId: number, rating: number) => {
    setFeedbackTargetMessageId(messageId);
    setFeedbackInitialRating(rating);
    setFeedbackModalOpen(true);
  };

  const handleCopyText = (content: string, messageId: number) => {
    navigator.clipboard.writeText(content);
    setCopiedMessageId(messageId);
    setTimeout(() => setCopiedMessageId(null), 2000);
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left Sidebar */}
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={loadConversationDetails}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onQuickQuery={(q) => handleSendMessage(q)}
      />

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col h-[calc(100vh-61px)] bg-bccl-dark relative">
        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
          {messages.length === 0 ? (
            <div className="max-w-3xl mx-auto py-12 text-center space-y-6">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500 to-amber-700 mx-auto flex items-center justify-center shadow-xl border border-amber-400/30">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <div className="space-y-2">
                <h2 className="text-2xl font-bold text-white tracking-tight">
                  BCCL Enterprise Knowledge Assistant
                </h2>
                <p className="text-sm text-bccl-muted max-w-lg mx-auto">
                  Ask natural language questions regarding the BCCL Conduct, Discipline and Appeal (CDA) Rules,
                  suspension procedures, penalties, and official administrative guidelines.
                </p>
              </div>

              {/* Sample Starters Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-4 text-left max-w-2xl mx-auto">
                {[
                  {
                    title: 'Rules for Suspension',
                    desc: 'What are the rules and subsistence allowance for suspension?',
                    query: 'What are the rules for suspension?'
                  },
                  {
                    title: 'Major & Minor Penalties',
                    desc: 'Explain the difference and list all major penalties.',
                    query: 'Explain major penalties.'
                  },
                  {
                    title: 'Misconduct Provisions',
                    desc: 'What specific acts of omission and commission constitute misconduct?',
                    query: 'What constitutes misconduct?'
                  },
                  {
                    title: 'Appeals Procedure',
                    desc: 'How many days does an employee have to file an appeal?',
                    query: 'Can an employee appeal a penalty?'
                  }
                ].map((card, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(card.query)}
                    className="p-4 bg-bccl-surface border border-bccl-border hover:border-amber-500/50 rounded-xl transition-all text-left group hover:bg-bccl-card active:scale-[0.98]"
                  >
                    <p className="text-xs font-bold text-amber-400 group-hover:text-amber-300">{card.title}</p>
                    <p className="text-xs text-bccl-muted mt-1 leading-relaxed">{card.desc}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((msg) => {
                const isUser = msg.sender === 'user';
                return (
                  <div
                    key={msg.id}
                    className={`flex items-start space-x-3 ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    {!isUser && (
                      <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center border border-amber-500/30 flex-shrink-0 mt-1">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}

                    <div
                      className={`max-w-[85%] rounded-2xl p-4 shadow-md ${
                        isUser
                          ? 'bg-amber-600 text-white rounded-br-none'
                          : 'bg-bccl-surface border border-bccl-border text-slate-100 rounded-bl-none prose-dark'
                      }`}
                    >
                      {/* Message Content */}
                      <div className="text-xs sm:text-sm whitespace-pre-wrap leading-relaxed">
                        {msg.content}
                      </div>

                      {/* Assistant Extra Metadata: Latency, Citations, Actions */}
                      {!isUser && (
                        <div className="mt-4 pt-3 border-t border-bccl-border/60 space-y-3">
                          {/* Citations Badges */}
                          {msg.citations && msg.citations.length > 0 && (
                            <div>
                              <p className="text-[11px] font-semibold text-amber-400/90 uppercase tracking-wider mb-1.5 flex items-center space-x-1">
                                <BookOpen className="w-3.5 h-3.5" />
                                <span>Verified Document Sources:</span>
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {msg.citations.map((cit, idx) => (
                                  <button
                                    key={idx}
                                    onClick={() => handleCitationClick(cit)}
                                    className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-bccl-card hover:bg-bccl-border/80 text-[11px] text-slate-200 border border-bccl-border hover:border-amber-500/40 transition-colors"
                                  >
                                    <span className="font-semibold text-amber-400">
                                      {cit.rule_number || `Page ${cit.page_number}`}
                                    </span>
                                    <span className="text-bccl-muted truncate max-w-[140px]">
                                      — {cit.document_name}
                                    </span>
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Footer Action Bar */}
                          <div className="flex items-center justify-between text-[11px] text-bccl-muted pt-1">
                            <div className="flex items-center space-x-2">
                              {msg.latency_ms > 0 && (
                                <span className="flex items-center space-x-1 font-mono text-[10px] text-slate-400 bg-bccl-card px-2 py-0.5 rounded border border-bccl-border">
                                  <Clock className="w-3 h-3 text-amber-500" />
                                  <span>{msg.latency_ms.toFixed(1)}ms</span>
                                </span>
                              )}
                            </div>

                            <div className="flex items-center space-x-1">
                              <button
                                onClick={() => handleCopyText(msg.content, msg.id)}
                                title="Copy answer"
                                className="p-1.5 hover:text-white hover:bg-bccl-card rounded-lg transition-colors"
                              >
                                {copiedMessageId === msg.id ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5" />
                                )}
                              </button>
                              <button
                                onClick={() => handleOpenFeedback(msg.id, 1)}
                                title="Helpful"
                                className="p-1.5 hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors"
                              >
                                <ThumbsUp className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleOpenFeedback(msg.id, -1)}
                                title="Unhelpful"
                                className="p-1.5 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                              >
                                <ThumbsDown className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {isUser && (
                      <div className="w-8 h-8 rounded-lg bg-amber-600/30 text-amber-400 flex items-center justify-center border border-amber-500/30 flex-shrink-0 mt-1">
                        <UserIcon className="w-4 h-4" />
                      </div>
                    )}
                  </div>
                );
              })}

              {loading && (
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center border border-amber-500/30 flex-shrink-0 animate-pulse">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="bg-bccl-surface border border-bccl-border rounded-2xl rounded-bl-none p-4 shadow-md flex items-center space-x-2">
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-bounce" />
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-bounce [animation-delay:0.2s]" />
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-bounce [animation-delay:0.4s]" />
                    <span className="text-xs text-bccl-muted ml-2">Retrieving official BCCL rules & synthesizing response...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="p-4 sm:p-6 border-t border-bccl-border bg-bccl-surface">
          <div className="max-w-3xl mx-auto">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="relative flex items-center"
            >
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder="Ask about BCCL CDA rules, suspension, penalties, misconduct, appeals..."
                className="w-full bg-bccl-dark border border-bccl-border rounded-2xl py-3.5 pl-4 pr-12 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 shadow-inner"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !inputQuery.trim()}
                className="absolute right-2.5 p-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white disabled:opacity-40 disabled:hover:bg-amber-600 transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
            <p className="text-center text-[10px] text-bccl-muted mt-2">
              Responses are strictly document-grounded in official BCCL CDA Rules. Non-pertinent queries will trigger explicit abstention.
            </p>
          </div>
        </div>
      </div>

      {/* Citation Inspector Drawer */}
      <CitationDrawer
        isOpen={citationDrawerOpen}
        citation={selectedCitation}
        onClose={() => setCitationDrawerOpen(false)}
      />

      {/* Feedback Modal */}
      <FeedbackModal
        isOpen={feedbackModalOpen}
        messageId={feedbackTargetMessageId}
        initialRating={feedbackInitialRating}
        onClose={() => setFeedbackModalOpen(false)}
        onSuccess={() => {}}
      />
    </div>
  );
}
