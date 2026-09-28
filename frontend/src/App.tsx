import React, { useState } from 'react';
import { useAuth } from './hooks/useAuth';
import { Header } from './components/Header';
import { Navbar } from './components/Navbar';
import { Landing } from './pages/landing/Landing';
import { SchemeSelection } from './pages/applicant/SchemeSelection';
import { ApplicationForm } from './pages/applicant/ApplicationForm';
import { StatusTracker } from './pages/applicant/StatusTracker';
import { ApplicantLogin } from './pages/applicant/ApplicantLogin';
import { ReviewQueue } from './pages/admin/ReviewQueue';
import { ApplicationDetail } from './pages/admin/ApplicationDetail';
import { SelectionDesk } from './pages/admin/SelectionDesk';
import { AwardManagement } from './pages/admin/AwardManagement';
import { Landmark, Shield, Award, Users, ArrowLeft } from 'lucide-react';

export const App: React.FC = () => {
  const { user, isAdmin, isRestoring, logout } = useAuth();

  // Tab navigation state
  const [currentTab, setCurrentTab] = useState<string>('schemes');
  const [selectedSchemeCode, setSelectedSchemeCode] = useState<string>('NFST');
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);

  // Public landing page shown before sign-in
  const [showLanding, setShowLanding] = useState(true);
  const [landingAuthMode, setLandingAuthMode] = useState<'login' | 'register'>('login');

  // If user switches role, adjust tab appropriately
  const handleSelectTab = (tab: string) => {
    setCurrentTab(tab);
  };

  // An officer lands on the review queue, an applicant on the scheme list.
  const handleSignedIn = () => {
    setCurrentTab(isAdmin ? 'admin-queue' : 'schemes');
  };

  const handleSignOut = () => {
    logout();
    setSelectedAppId(null);
    setCurrentTab('schemes');
    setShowLanding(true);
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
      {user && <Navbar currentTab={currentTab} onSelectTab={handleSelectTab} onSignOut={handleSignOut} />}

      {/* Main View Area */}
      <main className="flex-1">
        {isRestoring ? (
          <div className="flex flex-col items-center justify-center py-24 text-slate-500">
            <div className="inline-block animate-spin rounded-full h-9 w-9 border-4 border-blue-900 border-r-transparent mb-3" />
            <p className="text-xs">Restoring your session…</p>
          </div>
        ) : !user ? (
          showLanding ? (
            <Landing
              onGetStarted={() => {
                setLandingAuthMode('register');
                setShowLanding(false);
              }}
              onSignIn={() => {
                setLandingAuthMode('login');
                setShowLanding(false);
              }}
            />
          ) : (
            <div className="max-w-md mx-auto px-4 py-10">
              <button
                onClick={() => setShowLanding(true)}
                className="text-xs text-slate-500 hover:text-blue-900 mb-4 flex items-center gap-1.5 font-medium"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to home
              </button>
              <ApplicantLogin initialMode={landingAuthMode} onLoginSuccess={handleSignedIn} />
            </div>
          )
        ) : isAdmin ? (
          currentTab === 'admin-detail' && selectedAppId ? (
            <ApplicationDetail applicationId={selectedAppId} onBackToQueue={handleBackToQueue} />
          ) : currentTab === 'admin-selection' ? (
            <SelectionDesk onSelectApplication={handleSelectAppForReview} />
          ) : currentTab === 'admin-awards' ? (
            <AwardManagement />
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
