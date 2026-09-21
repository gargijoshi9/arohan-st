import React from 'react';
import { useAuth } from '../hooks/useAuth';
import { Landmark, User, Shield, CheckCircle } from 'lucide-react';

interface HeaderProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ currentTab, onSelectTab }) => {
  const { user, selectDemoProfile, logout } = useAuth();

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-50 shadow-sm">
      {/* Top Tiranga Subtle Strip */}
      <div className="h-1 bg-gradient-to-r from-amber-500 via-white to-emerald-600 border-b border-slate-200" />

      {/* Demo Persona Fast Switcher Bar (Hackathon Facilitator) */}
      <div className="bg-slate-900 text-slate-200 text-xs px-4 py-1.5 flex flex-wrap items-center justify-between gap-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="inline-block px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-medium tracking-wide text-[10px] uppercase">
            Hackathon Demo Switcher
          </span>
          <span className="hidden sm:inline text-slate-400">Switch persona:</span>
        </div>
        <div className="flex items-center gap-1.5 sm:gap-2">
          <button
            onClick={() => {
              selectDemoProfile('ramesh');
              onSelectTab('status');
            }}
            className={`px-2 py-0.5 rounded text-[11px] font-medium transition ${
              user?.name === 'Ramesh Chandra Munda'
                ? 'bg-blue-600 text-white font-semibold ring-1 ring-blue-300'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
            }`}
          >
            Applicant 1: Ramesh (NFST - Pass)
          </button>
          <button
            onClick={() => {
              selectDemoProfile('amit');
              onSelectTab('status');
            }}
            className={`px-2 py-0.5 rounded text-[11px] font-medium transition ${
              user?.name === 'Amit Tirkey'
                ? 'bg-rose-600 text-white font-semibold ring-1 ring-rose-300'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
            }`}
          >
            Applicant 2: Amit (NOS - Flagged)
          </button>
          <button
            onClick={() => {
              selectDemoProfile('officer');
              onSelectTab('admin-queue');
            }}
            className={`px-2.5 py-0.5 rounded text-[11px] font-medium transition flex items-center gap-1 ${
              user?.role === 'admin'
                ? 'bg-emerald-600 text-white font-semibold ring-1 ring-emerald-300'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
            }`}
          >
            <Shield className="w-3 h-3 text-emerald-300" />
            Admin: MoTA Officer
          </button>
        </div>
      </div>

      {/* Main Masthead */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div className="flex items-center gap-3.5">
          {/* Emblem Motif */}
          <div className="w-12 h-12 rounded-lg bg-blue-900 flex items-center justify-center text-amber-400 shadow-md border border-blue-800 flex-shrink-0">
            <Landmark className="w-7 h-7 text-amber-400" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-blue-950 flex items-center gap-2">
                AROHAN-ST
                <span className="text-xs font-normal px-2 py-0.5 rounded bg-blue-100 text-blue-900 border border-blue-200">
                  आरोहण - ST
                </span>
              </h1>
            </div>
            <p className="text-xs text-slate-600 font-medium flex items-center gap-1.5 mt-0.5">
              <span>Ministry of Tribal Affairs, Government of India</span>
              <span className="text-slate-300">•</span>
              <span className="text-slate-500">NFST & NOS AI Adjudication Platform</span>
            </p>
          </div>
        </div>

        {/* Current Active User Status */}
        <div className="flex items-center gap-3 self-end md:self-auto">
          {user ? (
            <div className="flex items-center gap-2.5 bg-slate-100 rounded-lg p-2 border border-slate-200 text-xs">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-white text-xs ${
                  user.role === 'admin' ? 'bg-emerald-700' : 'bg-blue-800'
                }`}
              >
                {user.name.charAt(0)}
              </div>
              <div className="text-left">
                <div className="font-semibold text-slate-900 leading-tight flex items-center gap-1">
                  <span>{user.name}</span>
                  {user.role === 'admin' ? (
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 font-medium">
                      Admin
                    </span>
                  ) : (
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-100 text-blue-800 font-medium">
                      ST Scholar
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-500">{user.email}</div>
              </div>
              <button
                onClick={logout}
                className="text-[11px] text-slate-500 hover:text-slate-800 underline ml-1"
              >
                Log Out
              </button>
            </div>
          ) : (
            <div className="text-xs text-slate-500">Not logged in</div>
          )}
        </div>
      </div>
    </header>
  );
};
