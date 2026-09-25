import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { UserCheck, ArrowRight, Lock } from 'lucide-react';

interface ApplicantLoginProps {
  onLoginSuccess: () => void;
}

export const ApplicantLogin: React.FC<ApplicantLoginProps> = ({ onLoginSuccess }) => {
  const { loginPortal } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const isOfficerEmail = email.trim().toLowerCase() === 'motaofficer@gmail.com';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (loginPortal(name, email, password)) {
      setError(null);
      onLoginSuccess();
    } else {
      setError('Incorrect MoTA officer password.');
    }
  };

  return (
    <div className="max-w-md mx-auto my-12 p-6 bg-white rounded-xl shadow-md border border-slate-200">
      <div className="text-center mb-6">
        <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-900 mx-auto flex items-center justify-center mb-3">
          <UserCheck className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">ST Scholar Portal Login</h2>
        <p className="text-xs text-slate-500 mt-1">
          Ministry of Tribal Affairs — Scholarship, Fellowship & Officer Access
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
          <input
            type="text"
            required={!isOfficerEmail}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
            placeholder="Enter your full name"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            {isOfficerEmail ? 'Officer Username (email)' : 'Email Address'}
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
            placeholder="Enter your email"
          />
        </div>

        {isOfficerEmail && (
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
                placeholder="Enter password"
              />
            </div>
          </div>
        )}

        {error && <p role="alert" className="text-xs text-rose-700">{error}</p>}

        <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-[11px] text-slate-600">
          <span className="font-semibold text-slate-700">Scheduled Tribe (ST) Verification:</span>{' '}
          In this prototype, applicant category is defaulted to ST with mock AI document rule verification.
        </div>

        <button
          type="submit"
          className="w-full py-2.5 px-4 bg-blue-900 hover:bg-blue-800 text-white font-medium text-sm rounded-lg shadow transition flex items-center justify-center gap-2"
        >
          <span>Continue to Portal</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
