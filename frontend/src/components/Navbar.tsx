import React from 'react';
import { useAuth } from '../hooks/useAuth';
import { BookOpen, FileEdit, CheckSquare, ShieldAlert, ListChecks, Award, LogOut } from 'lucide-react';

interface NavbarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  onSignOut: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, onSelectTab, onSignOut }) => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  return (
    <nav className="bg-blue-950 text-white shadow-inner">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between overflow-x-auto py-1">
          <div className="flex items-center space-x-1 sm:space-x-2 py-1">
            {!isAdmin ? (
              <>
                <button
                  onClick={() => onSelectTab('schemes')}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md text-xs sm:text-sm font-medium transition ${
                    currentTab === 'schemes'
                      ? 'bg-blue-800 text-white shadow'
                      : 'text-blue-100 hover:bg-blue-900 hover:text-white'
                  }`}
                >
                  <BookOpen className="w-4 h-4" />
                  <span>MoTA Schemes</span>
                </button>

                <button
                  onClick={() => onSelectTab('apply')}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md text-xs sm:text-sm font-medium transition ${
                    currentTab === 'apply'
                      ? 'bg-blue-800 text-white shadow'
                      : 'text-blue-100 hover:bg-blue-900 hover:text-white'
                  }`}
                >
                  <FileEdit className="w-4 h-4" />
                  <span>New Application</span>
                </button>

                <button
                  onClick={() => onSelectTab('status')}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md text-xs sm:text-sm font-medium transition ${
                    currentTab === 'status'
                      ? 'bg-blue-800 text-white shadow'
                      : 'text-blue-100 hover:bg-blue-900 hover:text-white'
                  }`}
                >
                  <CheckSquare className="w-4 h-4" />
                  <span>Track Status</span>
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => onSelectTab('admin-queue')}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-md text-xs sm:text-sm font-medium transition ${
                    currentTab === 'admin-queue' || currentTab === 'admin-detail'
                      ? 'bg-emerald-700 text-white shadow'
                      : 'text-emerald-100 hover:bg-emerald-800 hover:text-white'
                  }`}
                >
                  <ShieldAlert className="w-4 h-4" />
                  <span>Officer Verification Queue</span>
                </button>
                <button
                  onClick={() => onSelectTab('admin-selection')}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-md text-xs sm:text-sm font-medium transition ${
                    currentTab === 'admin-selection' ? 'bg-emerald-700 text-white shadow' : 'text-emerald-100 hover:bg-emerald-800'
                  }`}
                >
                  <ListChecks className="w-4 h-4" />
                  <span>Merit & Selection</span>
                </button>
                <button
                  onClick={() => onSelectTab('admin-awards')}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-md text-xs sm:text-sm font-medium transition ${
                    currentTab === 'admin-awards' ? 'bg-emerald-700 text-white shadow' : 'text-emerald-100 hover:bg-emerald-800'
                  }`}
                >
                  <Award className="w-4 h-4" />
                  <span>Awards & Payments</span>
                </button>
              </>
            )}
          </div>

          <div className="flex items-center gap-3 text-xs py-1 pl-3 sm:pl-0">
            <span className="text-slate-300 hidden md:inline" title={user?.email}>
              {user?.full_name}
            </span>
            <span
              className={`px-2 py-0.5 rounded font-medium ${
                isAdmin
                  ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700'
                  : 'bg-blue-900 text-blue-200 border border-blue-800'
              }`}
            >
              {isAdmin ? 'Adjudicator Desk' : 'Applicant Portal'}
            </span>
            <button
              onClick={onSignOut}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-100 font-semibold transition"
              title="Sign out"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};
