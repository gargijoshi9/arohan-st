import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { UserCheck, ArrowRight, Lock, Mail, Phone, UserPlus, LogIn } from 'lucide-react';

interface ApplicantLoginProps {
  onLoginSuccess: () => void;
  initialMode?: Mode;
}

type Mode = 'login' | 'register';

const inputClass =
  'w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none';
const fieldLabel = 'block text-xs font-semibold text-slate-700 mb-1';

export const ApplicantLogin: React.FC<ApplicantLoginProps> = ({ onLoginSuccess, initialMode = 'login' }) => {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>(initialMode);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === 'register') {
        await register({ full_name: fullName, email, phone, password });
      } else {
        await login(email, password);
      }
      onLoginSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-md mx-auto my-12 p-6 bg-white rounded-xl shadow-md border border-slate-200">
      <div className="text-center mb-6">
        <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-900 mx-auto flex items-center justify-center mb-3">
          <UserCheck className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          {mode === 'register' ? 'Create Applicant Account' : 'Portal Sign In'}
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Ministry of Tribal Affairs — Scholarship, Fellowship &amp; Officer Access
        </p>
      </div>

      <div className="flex mb-5 rounded-lg border border-slate-200 p-1 bg-slate-50 text-xs font-semibold">
        <button
          type="button"
          onClick={() => switchMode('login')}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md transition ${
            mode === 'login' ? 'bg-white text-blue-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <LogIn className="w-3.5 h-3.5" />
          Sign In
        </button>
        <button
          type="button"
          onClick={() => switchMode('register')}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md transition ${
            mode === 'register' ? 'bg-white text-blue-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <UserPlus className="w-3.5 h-3.5" />
          Register
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {mode === 'register' && (
          <div>
            <label className={fieldLabel} htmlFor="full-name">
              Full Name
            </label>
            <input
              id="full-name"
              type="text"
              required
              minLength={2}
              maxLength={120}
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className={inputClass}
              placeholder="Enter your full name as per your records"
            />
          </div>
        )}

        <div>
          <label className={fieldLabel} htmlFor="email">
            Email Address
          </label>
          <div className="relative">
            <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={`${inputClass} pl-9`}
              placeholder="you@example.com"
            />
          </div>
        </div>

        {mode === 'register' && (
          <div>
            <label className={fieldLabel} htmlFor="phone">
              Mobile Number <span className="font-normal text-slate-400">(optional)</span>
            </label>
            <div className="relative">
              <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                id="phone"
                type="tel"
                autoComplete="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className={`${inputClass} pl-9`}
                placeholder="Contact number"
              />
            </div>
          </div>
        )}

        <div>
          <label className={fieldLabel} htmlFor="password">
            Password
          </label>
          <div className="relative">
            <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              id="password"
              type="password"
              required
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`${inputClass} pl-9`}
              placeholder={mode === 'register' ? 'Create a password' : 'Enter your password'}
            />
          </div>
          {mode === 'register' && (
            <p className="mt-1 text-[10px] text-slate-500">
              Use at least 8 characters with a mix of upper and lower case letters and digits.
            </p>
          )}
        </div>

        {error && (
          <p role="alert" className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-[11px] text-slate-600">
          <span className="font-semibold text-slate-700">Account security:</span> Passwords are stored only as bcrypt
          hashes. Access to any applicant record is limited to the account that created it, and every officer action is
          written to the audit trail.
        </div>

        <button
          type="submit"
          disabled={busy}
          className="w-full py-2.5 px-4 bg-blue-900 hover:bg-blue-800 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium text-sm rounded-lg shadow transition flex items-center justify-center gap-2"
        >
          <span>{busy ? 'Please wait…' : mode === 'register' ? 'Create Account' : 'Sign In'}</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
