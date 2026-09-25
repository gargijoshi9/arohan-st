import React from 'react';
import { useAuth } from '../hooks/useAuth';
import { Landmark } from 'lucide-react';

export const Header: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-50 shadow-sm">
      {/* Top Tiranga Subtle Strip */}
      <div className="h-1 bg-gradient-to-r from-amber-500 via-white to-emerald-600 border-b border-slate-200" />

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
              <span className="text-slate-500">Scholarship & Fellowship Management Platform</span>
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
