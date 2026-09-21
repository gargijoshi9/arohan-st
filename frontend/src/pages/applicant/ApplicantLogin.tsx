import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { UserCheck, Shield, Sparkles, ArrowRight } from 'lucide-react';

interface ApplicantLoginProps {
  onLoginSuccess: () => void;
}

export const ApplicantLogin: React.FC<ApplicantLoginProps> = ({ onLoginSuccess }) => {
  const { loginApplicant, selectDemoProfile } = useAuth();
  const [name, setName] = useState('Ramesh Chandra Munda');
  const [email, setEmail] = useState('ramesh.munda@example.edu');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loginApplicant(name, email);
    onLoginSuccess();
  };

  return (
    <div className="max-w-md mx-auto my-12 p-6 bg-white rounded-xl shadow-md border border-slate-200">
      <div className="text-center mb-6">
        <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-900 mx-auto flex items-center justify-center mb-3">
          <UserCheck className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">ST Scholar Portal Login</h2>
        <p className="text-xs text-slate-500 mt-1">
          Ministry of Tribal Affairs — Direct Fellowship & Scholarship Access
        </p>
      </div>

      {/* Quick Demo Pre-fill */}
      <div className="mb-6 p-3 bg-blue-50/70 border border-blue-200 rounded-lg text-xs">
        <div className="font-semibold text-blue-900 mb-2 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-blue-700" />
          <span>Quick Demo Presets:</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => {
              selectDemoProfile('ramesh');
              onLoginSuccess();
            }}
            className="p-2 bg-white rounded border border-blue-200 hover:border-blue-500 text-left transition"
          >
            <div className="font-medium text-slate-800">Ramesh Munda</div>
            <div className="text-[10px] text-slate-500">NFST Fellow (Pass)</div>
          </button>
          <button
            type="button"
            onClick={() => {
              selectDemoProfile('amit');
              onLoginSuccess();
            }}
            className="p-2 bg-white rounded border border-rose-200 hover:border-rose-400 text-left transition"
          >
            <div className="font-medium text-slate-800">Amit Tirkey</div>
            <div className="text-[10px] text-rose-600">NOS (Income Flagged)</div>
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
            placeholder="Enter your full name"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
            placeholder="Enter your email"
          />
        </div>

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
