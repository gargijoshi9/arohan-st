import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Shield, Lock, ArrowRight } from 'lucide-react';

interface AdminLoginProps {
  onLoginSuccess: () => void;
}

export const AdminLogin: React.FC<AdminLoginProps> = ({ onLoginSuccess }) => {
  const { loginAdmin } = useAuth();
  const [officerName, setOfficerName] = useState('Dr. Arjun K. Meena');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loginAdmin(officerName);
    onLoginSuccess();
  };

  return (
    <div className="max-w-md mx-auto my-12 p-6 bg-white rounded-xl shadow-md border border-slate-200">
      <div className="text-center mb-6">
        <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-800 mx-auto flex items-center justify-center mb-3">
          <Shield className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">MoTA Adjudication Desk</h2>
        <p className="text-xs text-slate-500 mt-1">
          Ministry of Tribal Affairs — Scholarship & Fellowship Officer Login
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Officer Name / ID</label>
          <input
            type="text"
            required
            value={officerName}
            onChange={(e) => setOfficerName(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">MoTA Desk Passcode (Mock)</label>
          <div className="relative">
            <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="password"
              value="••••••••••••"
              disabled
              className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 bg-slate-100 rounded-lg text-slate-500 cursor-not-allowed"
            />
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Mock authentication enabled for demo evaluation.</p>
        </div>

        <button
          type="submit"
          className="w-full py-2.5 px-4 bg-emerald-800 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg shadow transition flex items-center justify-center gap-2"
        >
          <span>Access Verification Queue</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
