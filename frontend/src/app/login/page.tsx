'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, Cpu, Lock, User as UserIcon, ArrowRight, CheckCircle2, AlertCircle } from 'lucide-react';
import { loginApi, registerApi } from '../../lib/api';
import { saveAuthToken } from '../../lib/auth';

export default function LoginPage() {
  const router = useRouter();
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [department, setDepartment] = useState('Operations');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (isRegister) {
        await registerApi({
          username,
          email,
          password,
          full_name: fullName,
          department
        });
      }
      const data = await loginApi(username, password);
      saveAuthToken(data.access_token, {
        username: data.username,
        role: data.role,
        full_name: data.full_name
      });
      router.push('/');
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (user: string, pass: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await loginApi(user, pass);
      saveAuthToken(data.access_token, {
        username: data.username,
        role: data.role,
        full_name: data.full_name
      });
      router.push('/');
    } catch (err: any) {
      setError(err.message || 'Quick login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-bccl-dark p-4 relative overflow-hidden">
      {/* Background glow accents */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-bccl-surface border border-bccl-border rounded-3xl p-8 shadow-2xl relative z-10">
        {/* Header */}
        <div className="text-center space-y-3 mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-500 to-amber-700 mx-auto flex items-center justify-center shadow-xl border border-amber-400/30">
            <Cpu className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide">
              Bharat Coking Coal Limited
            </h1>
            <p className="text-xs text-bccl-muted mt-0.5">Enterprise AI Knowledge Retrieval Platform</p>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-950/50 border border-red-500/40 rounded-xl flex items-center space-x-2 text-xs text-red-300">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Auth Form */}
        <form onSubmit={handleLoginSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-bccl-muted uppercase tracking-wider mb-1">
              Username
            </label>
            <div className="relative">
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                className="w-full bg-bccl-dark border border-bccl-border rounded-xl py-2.5 pl-10 pr-4 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                required
              />
              <UserIcon className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
            </div>
          </div>

          {isRegister && (
            <>
              <div>
                <label className="block text-xs font-semibold text-bccl-muted uppercase tracking-wider mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@bccl.gov.in"
                  className="w-full bg-bccl-dark border border-bccl-border rounded-xl py-2.5 px-4 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-bccl-muted uppercase tracking-wider mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Aditya Kumar Jha"
                  className="w-full bg-bccl-dark border border-bccl-border rounded-xl py-2.5 px-4 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-semibold text-bccl-muted uppercase tracking-wider mb-1">
              Password
            </label>
            <div className="relative">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-bccl-dark border border-bccl-border rounded-xl py-2.5 pl-10 pr-4 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                required
              />
              <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white font-semibold py-3 px-4 rounded-xl shadow-lg transition-all border border-amber-400/20 active:scale-[0.98] text-sm disabled:opacity-50 mt-2"
          >
            <span>{isRegister ? 'Create Account' : 'Sign In to Portal'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        {/* Quick Demo Access Switchers */}
        <div className="mt-8 pt-6 border-t border-bccl-border space-y-3">
          <p className="text-center text-[11px] font-semibold text-bccl-muted uppercase tracking-wider">
            Quick One-Click Demo Access
          </p>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => handleQuickLogin('admin', 'admin123')}
              className="p-3 bg-bccl-card border border-bccl-border hover:border-amber-500/50 rounded-xl text-left transition-all group hover:bg-bccl-border/40"
            >
              <p className="text-xs font-bold text-amber-400">Admin Portal</p>
              <p className="text-[10px] text-bccl-muted font-mono">admin / admin123</p>
            </button>

            <button
              onClick={() => handleQuickLogin('user', 'user123')}
              className="p-3 bg-bccl-card border border-bccl-border hover:border-blue-500/50 rounded-xl text-left transition-all group hover:bg-bccl-border/40"
            >
              <p className="text-xs font-bold text-blue-400">Executive User</p>
              <p className="text-[10px] text-bccl-muted font-mono">user / user123</p>
            </button>
          </div>
        </div>

        <div className="mt-6 text-center">
          <button
            onClick={() => setIsRegister(!isRegister)}
            className="text-xs text-amber-400 hover:underline"
          >
            {isRegister ? 'Already registered? Sign in instead' : 'New employee? Register account'}
          </button>
        </div>
      </div>
    </div>
  );
}
