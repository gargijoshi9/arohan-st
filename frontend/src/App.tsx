import React, { useState } from 'react';
import { useAuth } from './hooks/useAuth';
import { Header } from './components/Header';
import { Navbar } from './components/Navbar';
import { SchemeSelection } from './pages/applicant/SchemeSelection';
import { ApplicationForm } from './pages/applicant/ApplicationForm';
import { StatusTracker } from './pages/applicant/StatusTracker';
import { ApplicantLogin } from './pages/applicant/ApplicantLogin';
import { ReviewQueue } from './pages/admin/ReviewQueue';
import { ApplicationDetail } from './pages/admin/ApplicationDetail';
import { Landmark, Shield, Award, Users } from 'lucide-react';

export const App: React.FC = () => {
  const { user, isAdmin } = useAuth();

  // Tab navigation state
  const [currentTab, setCurrentTab] = useState<string>('schemes');
  const [selectedSchemeCode, setSelectedSchemeCode] = useState<string>('NFST');
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);

  // If user switches role, adjust tab appropriately
  const handleSelectTab = (tab: string) => {
    setCurrentTab(tab);
  };

  const handleSelectSchemeToApply = (schemeCode: string) => {
    setSelectedSchemeCode(schemeCode);
    setCurrentTab('apply');
  };

  const handleApplicationSubmitted = (appId: number) => {
    setSelectedAppId(appId);
    setCurrentTab('status');
  };

  const handleSelectAppForReview = (appId: number) => {
    setSelectedAppId(appId);
    setCurrentTab('admin-detail');
  };

  const handleBackToQueue = () => {
    setSelectedAppId(null);
    setCurrentTab('admin-queue');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-800">
      {/* Header */}
      <Header />

      {/* Navigation */}
      {user && <Navbar currentTab={currentTab} onSelectTab={handleSelectTab} />}

      {/* Main View Area */}
      <main className="flex-1">
        {!user ? (
          <div className="max-w-md mx-auto px-4 py-10">
            <ApplicantLogin onLoginSuccess={() => setCurrentTab('schemes')} />
          </div>
        ) : isAdmin ? (
          // ADMIN DESK
          currentTab === 'admin-detail' && selectedAppId ? (
            <ApplicationDetail
              applicationId={selectedAppId}
              onBackToQueue={handleBackToQueue}
            />
          ) : (
            <ReviewQueue onSelectApplication={handleSelectAppForReview} />
          )
        ) : (
          // APPLICANT PORTAL
          currentTab === 'apply' ? (
            <ApplicationForm
              initialSchemeCode={selectedSchemeCode}
              onBackToSchemes={() => setCurrentTab('schemes')}
              onSubmitSuccess={handleApplicationSubmitted}
            />
          ) : currentTab === 'status' ? (
            <StatusTracker
              highlightAppId={selectedAppId || undefined}
              onApplyNew={() => setCurrentTab('schemes')}
            />
          ) : (
            <SchemeSelection onSelectScheme={handleSelectSchemeToApply} />
          )
        )}
      </main>

      {/* Portal Footer */}
      <footer className="bg-slate-900 text-slate-400 text-xs border-t border-slate-800 mt-12 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 text-center md:text-left">
              <div className="w-8 h-8 rounded bg-blue-950 border border-blue-800 flex items-center justify-center text-amber-400">
                <Landmark className="w-4 h-4" />
              </div>
              <div>
                <div className="text-slate-200 font-bold">AROHAN-ST Prototype Platform</div>
                <div className="text-[11px] text-slate-400">
                  MoTA ST Scholarship & Fellowship Schemes
                </div>
              </div>
            </div>

            <div className="text-center md:text-right text-[11px] text-slate-500">
              <div>Designed for Ministry of Tribal Affairs (MoTA) Fellowship Adjudication</div>
              <div className="mt-1">
                Configurable eligibility rules • Officer review required • Hackathon prototype
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
