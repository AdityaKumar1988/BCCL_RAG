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
  Search,
  Mic,
  MicOff,
  Square,
  Database,
  Layers,
  Volume2,
  XCircle
} from 'lucide-react';
import Sidebar from '../components/Sidebar';
import CitationDrawer from '../components/CitationDrawer';
import FeedbackModal from '../components/FeedbackModal';
import {
  getConversationsApi,
  getConversationApi,
  deleteConversationApi,
  sendChatMessageApi,
  sendVoiceChatApi,
  Conversation,
  Message,
  Citation
} from '../lib/api';
import { isAuthenticated } from '../lib/auth';
import { extractKeyPointsSummary } from '../lib/ttsSummary';

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

  // Knowledge Base Selection state: 'BCCL_Rules' (new), 'CDA_Rules' (existing), 'all' (unified)
  const [selectedKb, setSelectedKb] = useState<'BCCL_Rules' | 'CDA_Rules' | 'all'>('BCCL_Rules');

  // Web Speech API Voice recording & live transcript state
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [finalTranscript, setFinalTranscript] = useState('');
  const [voiceError, setVoiceError] = useState<string | null>(null);

  // Text-to-Speech active speaking message state
  const [speakingMessageId, setSpeakingMessageId] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const transcriptTextRef = useRef<{ final: string; interim: string }>({ final: '', interim: '' });
  const hasSubmittedRef = useRef<boolean>(false);

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

  // Clean up recording timer, recognition, and speech synthesis on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
      }
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

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

  // Text message handler
  const handleSendMessage = async (queryText?: string) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim() || loading) return;

    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setSpeakingMessageId(null);
    }

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
      const res = await sendChatMessageApi(textToSend, activeConversationId, selectedKb);

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

  // Voice message handler - routes recognized speech text directly to /api/chat with DistilBERT intent routing
  const handleSendVoiceQuery = async (speechText: string) => {
    const textToSend = speechText.trim();
    if (!textToSend || loading) return;

    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setSpeakingMessageId(null);
    }

    const userMsgTemp: Message = {
      id: Date.now(),
      conversation_id: activeConversationId || 0,
      sender: 'user',
      content: textToSend,
      is_voice: true,
      recognized_speech: textToSend,
      citations: [],
      latency_ms: 0,
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, userMsgTemp]);
    setLoading(true);

    try {
      const res = await sendChatMessageApi(textToSend, activeConversationId, selectedKb);

      const asstMsg: Message = {
        id: res.message_id,
        conversation_id: res.conversation_id,
        sender: 'assistant',
        content: res.answer,
        detected_intent: res.detected_intent || res.intent,
        intent_confidence: res.intent_confidence !== undefined ? res.intent_confidence : res.confidence,
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

  // Start Voice Recording using Browser Web Speech API
  const handleStartRecording = () => {
    setVoiceError(null);

    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setSpeakingMessageId(null);
    }

    const SpeechRecognitionClass =
      typeof window !== 'undefined'
        ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
        : null;

    if (!SpeechRecognitionClass) {
      setVoiceError('Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.');
      return;
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) {}
    }

    setInterimTranscript('');
    setFinalTranscript('');
    transcriptTextRef.current = { final: '', interim: '' };
    hasSubmittedRef.current = false;

    try {
      const recognition = new SpeechRecognitionClass();
      recognition.lang = 'en-US';
      recognition.interimResults = true;
      recognition.continuous = false;

      recognition.onstart = () => {
        setIsRecording(true);
        setRecordingDuration(0);
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = setInterval(() => {
          setRecordingDuration((prev) => prev + 1);
        }, 1000);
      };

      recognition.onresult = (event: any) => {
        let interim = '';
        let final = '';

        for (let i = 0; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) {
            final += result[0].transcript + ' ';
          } else {
            interim += result[0].transcript;
          }
        }

        const cleanFinal = final.trim();
        const cleanInterim = interim.trim();
        setFinalTranscript(cleanFinal);
        setInterimTranscript(cleanInterim);
        transcriptTextRef.current = { final: cleanFinal, interim: cleanInterim };
      };

      recognition.onerror = (event: any) => {
        console.warn('SpeechRecognition error:', event.error);
        if (event.error === 'no-speech') {
          setVoiceError('No speech was detected. Please try again.');
        } else if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          setVoiceError('Microphone permission was denied. Please allow microphone access in your browser settings.');
        } else if (event.error === 'aborted') {
          // User stopped or canceled intentionally
        } else {
          setVoiceError(`Speech recognition error: ${event.error || 'Unknown error'}`);
        }
      };

      recognition.onend = () => {
        setIsRecording(false);
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        setRecordingDuration(0);

        // If not already submitted (e.g. user stopped speaking naturally)
        if (!hasSubmittedRef.current) {
          const fullText = (
            transcriptTextRef.current.final + ' ' + transcriptTextRef.current.interim
          ).trim();
          if (fullText) {
            hasSubmittedRef.current = true;
            handleSendVoiceQuery(fullText);
          }
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err: any) {
      console.error('Failed to initialize Web Speech API:', err);
      setVoiceError(err.message || 'Failed to initialize microphone speech recognition.');
    }
  };

  // Stop Voice Recording & submit recognized speech
  const handleStopRecording = () => {
    if (!isRecording) return;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsRecording(false);
    setRecordingDuration(0);

    const fullText = (
      transcriptTextRef.current.final + ' ' + transcriptTextRef.current.interim
    ).trim();

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }

    if (fullText && !hasSubmittedRef.current) {
      hasSubmittedRef.current = true;
      handleSendVoiceQuery(fullText);
    } else if (!fullText) {
      setVoiceError('No speech was detected. Please try again.');
    }
  };

  // Cancel Voice Recording without sending
  const handleCancelRecording = () => {
    hasSubmittedRef.current = true; // prevent onend from submitting
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) {}
      recognitionRef.current = null;
    }
    setIsRecording(false);
    setRecordingDuration(0);
    setInterimTranscript('');
    setFinalTranscript('');
    transcriptTextRef.current = { final: '', interim: '' };
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

  // Toggle Text-to-Speech (TTS) reading of key points
  const handleToggleSpeech = (messageId: number, content: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setVoiceError('Text-to-speech is not supported in this browser.');
      return;
    }

    if (speakingMessageId === messageId) {
      window.speechSynthesis.cancel();
      setSpeakingMessageId(null);
      return;
    }

    window.speechSynthesis.cancel();

    const summaryText = extractKeyPointsSummary(content);
    if (!summaryText) return;

    const utterance = new SpeechSynthesisUtterance(summaryText);
    utterance.lang = 'en-US';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Prefer an English voice if available
    try {
      const voices = window.speechSynthesis.getVoices();
      if (voices && voices.length > 0) {
        const preferredVoice =
          voices.find((v) => v.lang === 'en-US') ||
          voices.find((v) => v.lang.startsWith('en')) ||
          voices[0];
        if (preferredVoice) {
          utterance.voice = preferredVoice;
        }
      }
    } catch (e) {
      // Fallback to browser default voice
    }

    utterance.onstart = () => {
      setSpeakingMessageId(messageId);
    };

    utterance.onend = () => {
      setSpeakingMessageId(null);
    };

    utterance.onerror = (e) => {
      console.warn('SpeechSynthesis error:', e);
      setSpeakingMessageId(null);
    };

    window.speechSynthesis.speak(utterance);
  };

  const formatSeconds = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
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
        {/* Knowledge Base Selector & Engine Header */}
        <div className="px-4 sm:px-6 py-2.5 bg-bccl-card/90 border-b border-bccl-border flex flex-wrap items-center justify-between gap-2 z-10">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-bccl-muted flex items-center space-x-1.5">
              <Database className="w-3.5 h-3.5 text-amber-400" />
              <span>Knowledge Base:</span>
            </span>
            <div className="inline-flex rounded-lg bg-bccl-dark p-0.5 border border-bccl-border">
              <button
                type="button"
                onClick={() => setSelectedKb('BCCL_Rules')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  selectedKb === 'BCCL_Rules'
                    ? 'bg-amber-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Search BCCL Rules (amended CDA Rules up to July 2006, 55 pages)"
              >
                BCCL Rules
              </button>
              <button
                type="button"
                onClick={() => setSelectedKb('CDA_Rules')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  selectedKb === 'CDA_Rules'
                    ? 'bg-amber-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Search baseline CDA Rules documents"
              >
                CDA Rules
              </button>
              <button
                type="button"
                onClick={() => setSelectedKb('all')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  selectedKb === 'all'
                    ? 'bg-amber-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Search across all active knowledge bases"
              >
                All Sources
              </button>
            </div>
          </div>

          {/* Engine Capability Status Indicators */}
          <div className="flex items-center space-x-3 text-[11px] text-slate-400">
            <span className="flex items-center space-x-1.5 bg-bccl-dark/80 px-2 py-1 rounded border border-bccl-border">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-emerald-400 font-mono">DistilBERT Intent</span>
            </span>
            <span className="flex items-center space-x-1.5 bg-bccl-dark/80 px-2 py-1 rounded border border-bccl-border">
              <Mic className="w-3 h-3 text-amber-400" />
              <span className="text-amber-300 font-mono">Web Speech STT</span>
            </span>
          </div>
        </div>

        {/* Voice Error Banner */}
        {voiceError && (
          <div className="mx-4 sm:mx-6 mt-3 p-3 bg-red-950/60 border border-red-500/40 rounded-xl flex items-center justify-between text-xs text-red-200">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <span>{voiceError}</span>
            </div>
            <button
              onClick={() => setVoiceError(null)}
              className="text-red-400 hover:text-white p-1"
            >
              <XCircle className="w-4 h-4" />
            </button>
          </div>
        )}

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
                  Ask questions via voice or text regarding BCCL Conduct, Discipline and Appeal (CDA) Rules,
                  suspension procedures, penalties, and official administrative guidelines.
                </p>
              </div>

              {/* Sample Starters Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-4 text-left max-w-2xl mx-auto">
                {[
                  {
                    title: 'Rules for Suspension',
                    desc: 'What are the rules and subsistence allowance for suspension?',
                    query: 'What are the rules regarding suspension?'
                  },
                  {
                    title: 'Major & Minor Penalties',
                    desc: 'Explain the difference and list all major penalties.',
                    query: 'Explain major and minor penalties.'
                  },
                  {
                    title: 'Misconduct Provisions',
                    desc: 'What specific acts of omission and commission constitute misconduct?',
                    query: 'What constitutes misconduct under BCCL rules?'
                  },
                  {
                    title: 'Appeals Procedure',
                    desc: 'How many days does an employee have to file an appeal?',
                    query: 'What is the procedure and time limit for filing an appeal?'
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
                      {/* User Voice Input Badge & Recognized Speech Header */}
                      {isUser && msg.is_voice && (
                        <div className="flex items-center space-x-1.5 text-[11px] font-semibold text-amber-200/90 mb-1 pb-1 border-b border-amber-500/30">
                          <Mic className="w-3.5 h-3.5 text-amber-200 animate-pulse" />
                          <span>Voice Input • Recognized Speech:</span>
                        </div>
                      )}

                      {/* Assistant Detected Intent Badge */}
                      {!isUser && msg.detected_intent && (
                        <div className="mb-3 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/25 flex flex-wrap items-center justify-between gap-1.5">
                          <div className="flex items-center space-x-2">
                            <Sparkles className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                            <span className="text-[11px] text-amber-300 font-semibold uppercase tracking-wider">
                              Detected Intent:
                            </span>
                            <span className="text-xs font-mono font-bold text-white bg-amber-600/40 px-2 py-0.5 rounded border border-amber-500/40">
                              {msg.detected_intent.replace(/_/g, ' ')}
                            </span>
                          </div>
                          {msg.intent_confidence !== undefined && (
                            <span className="text-[10px] text-bccl-muted font-mono">
                              Confidence: {(msg.intent_confidence * 100).toFixed(1)}%
                            </span>
                          )}
                        </div>
                      )}

                      {/* Message Content */}
                      <div className="text-xs sm:text-sm whitespace-pre-wrap leading-relaxed">
                        {isUser && msg.is_voice
                          ? `"${msg.recognized_speech || msg.content || 'Voice message'}"`
                          : msg.content}
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
                                onClick={() => handleToggleSpeech(msg.id, msg.content)}
                                title={speakingMessageId === msg.id ? 'Stop Reading' : 'Listen to Key Points'}
                                className={`px-2 py-1 flex items-center space-x-1.5 rounded-lg text-[11px] font-medium transition-colors ${
                                  speakingMessageId === msg.id
                                    ? 'text-amber-300 bg-amber-500/20 border border-amber-500/40 animate-pulse'
                                    : 'text-slate-400 hover:text-amber-400 hover:bg-bccl-card'
                                }`}
                              >
                                {speakingMessageId === msg.id ? (
                                  <>
                                    <Square className="w-3 h-3 fill-current text-amber-400" />
                                    <span>Stop Reading</span>
                                  </>
                                ) : (
                                  <>
                                    <Volume2 className="w-3.5 h-3.5" />
                                    <span>Listen to Key Points</span>
                                  </>
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

              {/* Text Loading State */}
              {loading && (
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center border border-amber-500/30 flex-shrink-0 animate-pulse">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="bg-bccl-surface border border-bccl-border rounded-2xl rounded-bl-none p-4 shadow-md flex items-center space-x-2">
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-bounce" />
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-bounce [animation-delay:0.2s]" />
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-bounce [animation-delay:0.4s]" />
                    <span className="text-xs text-bccl-muted ml-2">
                      Searching {selectedKb === 'BCCL_Rules' ? 'BCCL Rules' : selectedKb === 'CDA_Rules' ? 'CDA Rules' : 'All Knowledge Bases'} & synthesizing response...
                    </span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Bar with Voice Recording Controls */}
        <div className="p-4 sm:p-6 border-t border-bccl-border bg-bccl-surface">
          <div className="max-w-3xl mx-auto">
            {isRecording ? (
              /* Active Voice Recording Bar with Real-Time Transcription Display */
              <div className="bg-red-950/40 border border-red-500/60 rounded-2xl p-4 shadow-lg space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="relative flex items-center justify-center">
                      <div className="w-3.5 h-3.5 rounded-full bg-red-500 animate-ping absolute" />
                      <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
                    </div>
                    <span className="text-sm font-semibold text-red-300 flex items-center space-x-1.5">
                      <span>Listening...</span>
                      <span className="font-mono text-xs text-red-400">({formatSeconds(recordingDuration)})</span>
                    </span>
                    <span className="text-xs text-red-400/80 hidden sm:inline">
                      Speak your question clearly
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={handleCancelRecording}
                      className="px-3 py-1.5 text-xs text-slate-300 hover:text-white rounded-lg hover:bg-bccl-card transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleStopRecording}
                      className="px-3.5 py-1.5 text-xs font-semibold text-white bg-red-600 hover:bg-red-500 rounded-xl shadow-md transition-colors flex items-center space-x-1.5"
                    >
                      <Square className="w-3 h-3 fill-current" />
                      <span>Stop & Search</span>
                    </button>
                  </div>
                </div>

                {/* Real-Time Live Transcript Display Box */}
                <div className="min-h-[46px] bg-bccl-dark/80 rounded-xl px-3.5 py-2.5 border border-red-500/30 text-xs sm:text-sm flex items-center">
                  {finalTranscript || interimTranscript ? (
                    <p className="leading-relaxed">
                      <span className="text-white font-medium">{finalTranscript}</span>
                      {interimTranscript && (
                        <span className="text-amber-300 italic ml-1.5">{interimTranscript}...</span>
                      )}
                    </p>
                  ) : (
                    <p className="text-slate-400 italic text-xs">
                      Speak now — your recognized speech will appear here in real time...
                    </p>
                  )}
                </div>
              </div>
            ) : (
              /* Standard Text + Voice Trigger Input Form */
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
                  placeholder="Ask a question or click the microphone to speak..."
                  className="w-full bg-bccl-dark border border-bccl-border rounded-2xl py-3.5 pl-4 pr-24 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 shadow-inner"
                  disabled={loading}
                />
                
                {/* Voice Record Button */}
                <button
                  type="button"
                  onClick={handleStartRecording}
                  disabled={loading}
                  title="Click to speak (Voice-enabled with Web Speech API & DistilBERT Intent Classifier)"
                  className="absolute right-12 p-2 rounded-xl text-slate-400 hover:text-amber-400 hover:bg-bccl-card transition-colors disabled:opacity-40"
                >
                  <Mic className="w-4 h-4" />
                </button>

                {/* Text Send Button */}
                <button
                  type="submit"
                  disabled={loading || !inputQuery.trim()}
                  className="absolute right-2.5 p-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white disabled:opacity-40 disabled:hover:bg-amber-600 transition-colors"
                  title="Send question"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            )}

            <p className="text-center text-[10px] text-bccl-muted mt-2">
              Responses are strictly document-grounded in official BCCL / CDA Rules. Non-pertinent queries will trigger explicit abstention.
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
