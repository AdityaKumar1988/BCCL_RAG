import { User } from './api';

export function saveAuthToken(token: string, user: { username: string; role: string; full_name?: string }) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('bccl_token', token);
    localStorage.setItem('bccl_user', JSON.stringify(user));
  }
}

export function getStoredUser(): { username: string; role: string; full_name?: string } | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem('bccl_user');
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function logout() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('bccl_token');
    localStorage.removeItem('bccl_user');
    window.location.href = '/login';
  }
}

export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  return !!localStorage.getItem('bccl_token');
}
