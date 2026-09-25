'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Shield, BookOpen, MessageSquare, Settings, LogOut, User, Cpu } from 'lucide-react';
import { getStoredUser, logout } from '../lib/auth';

export default function Navbar() {
  const pathname = usePathname();
  const [currentUser, setCurrentUser] = useState<{ username: string; role: string; full_name?: string } | null>(null);

  useEffect(() => {
    setCurrentUser(getStoredUser());
  }, [pathname]);

  if (pathname === '/login') return null;

  return (
    <header className="bg-bccl-surface border-b border-bccl-border sticky top-0 z-40 px-4 lg:px-8 py-3 flex items-center justify-between shadow-lg">
      <div className="flex items-center space-x-4">
        <Link href="/" className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center shadow-md border border-amber-400/30">
            <Cpu className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-wider text-white">BCCL AI RAG</span>
              <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 font-semibold border border-amber-500/30">
                PROTOTYPE
              </span>
            </div>
            <p className="text-[11px] text-bccl-muted font-medium">Bharat Coking Coal Limited | Enterprise Knowledge Retrieval</p>
          </div>
        </Link>
      </div>

      <nav className="flex items-center space-x-1 sm:space-x-3">
        <Link
          href="/"
          className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            pathname === '/'
              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
              : 'text-bccl-muted hover:text-white hover:bg-bccl-card'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span className="hidden sm:inline">AI Assistant</span>
        </Link>

        <Link
          href="/explorer"
          className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            pathname === '/explorer'
              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
              : 'text-bccl-muted hover:text-white hover:bg-bccl-card'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span className="hidden sm:inline">Knowledge Explorer</span>
        </Link>

        {currentUser?.role === 'admin' && (
          <Link
            href="/admin"
            className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              pathname === '/admin'
                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                : 'text-bccl-muted hover:text-white hover:bg-bccl-card'
            }`}
          >
            <Settings className="w-4 h-4" />
            <span className="hidden sm:inline">Admin Panel</span>
          </Link>
        )}

        <div className="h-6 w-px bg-bccl-border mx-2" />

        {currentUser ? (
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 bg-bccl-card px-3 py-1.5 rounded-lg border border-bccl-border">
              <User className="w-4 h-4 text-amber-400" />
              <div className="text-left">
                <p className="text-xs font-semibold text-white">{currentUser.username}</p>
                <p className="text-[10px] text-amber-400 uppercase font-mono">{currentUser.role}</p>
              </div>
            </div>
            <button
              onClick={logout}
              title="Logout"
              className="p-2 text-bccl-muted hover:text-red-400 hover:bg-red-500/10 rounded-lg border border-transparent hover:border-red-500/20 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            className="px-4 py-1.5 text-sm font-semibold rounded-lg bg-amber-600 hover:bg-amber-500 text-white transition-colors"
          >
            Login
          </Link>
        )}
      </nav>
    </header>
  );
}
