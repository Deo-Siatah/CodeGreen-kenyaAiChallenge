import { useState, useEffect } from 'react';
import { 
  ShieldCheck, LayoutDashboard, Users, Award, ShieldAlert, 
  RefreshCw, Zap, Database 
} from 'lucide-react';
import { Dashboard } from './components/Dashboard';
import { FarmerList } from './components/FarmerList';
import { FarmerDetail } from './components/FarmerDetail';
import { TestifiersView } from './components/TestifiersView';
import { type Farmer, type FinalResult, api, MOCK_VERIFICATION_RESULTS } from './services/api';

function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'farmers' | 'testifiers'>('dashboard');
  const [selectedFarmerId, setSelectedFarmerId] = useState<string | null>(null);
  
  const [farmers, setFarmers] = useState<Farmer[]>([]);
  const [results, setResults] = useState<Record<string, FinalResult>>({});
  const [loading, setLoading] = useState(true);
  const [apiOnline, setApiOnline] = useState(false);
  const [mockMode, setMockMode] = useState(api.isMockMode());
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Check API health
  const checkApi = async () => {
    const isOnline = await api.testConnection();
    setApiOnline(isOnline);
    return isOnline;
  };

  // Load all farmers and their results
  const loadData = async () => {
    setLoading(true);
    try {
      const isOnline = await checkApi();
      
      // Auto toggle to mock mode if backend is offline and nothing was explicitly chosen
      if (!isOnline && localStorage.getItem('hifadhi_use_mock') === null) {
        api.setMockMode(true);
        setMockMode(true);
      }

      const farmerList = await api.getFarmers();
      setFarmers(farmerList);

      // Load results for all farmers
      const resultsMap: Record<string, FinalResult> = {};
      for (const f of farmerList) {
        const res = await api.getVerificationResult(f.id);
        if (res) {
          resultsMap[f.id] = res;
        } else if (mockMode) {
          // Fill from mock
          const mockRes = MOCK_VERIFICATION_RESULTS[f.id];
          if (mockRes) resultsMap[f.id] = mockRes;
        }
      }
      setResults(resultsMap);
    } catch (e) {
      console.error('Error loading application data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [mockMode]);

  // Handle mock mode toggle
  const handleToggleMock = (enable: boolean) => {
    api.setMockMode(enable);
    setMockMode(enable);
    setStatusMessage(enable ? 'Switched to Demo Sandbox Mode' : 'Connected to Live Local API');
    setTimeout(() => setStatusMessage(null), 3000);
  };

  // Handle start verification for a farmer
  const handleStartVerification = async (farmerId: string) => {
    setLoading(true);
    try {
      await api.startVerification(farmerId);
      setStatusMessage('Alternative trust verification session started successfully.');
      setTimeout(() => setStatusMessage(null), 3000);
      
      // Reload details
      await loadData();
      setSelectedFarmerId(farmerId);
    } catch (e) {
      alert('Error initiating verification session');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      
      {/* Premium Top Navigation Bar */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => { setActiveTab('dashboard'); setSelectedFarmerId(null); }}>
            <div className="p-2 bg-gradient-to-br from-teal-500 to-amber-500 rounded-xl shadow-md">
              <ShieldCheck className="w-6 h-6 text-slate-950 stroke-[2.5]" />
            </div>
            <div>
              <h1 className="text-lg font-extrabold tracking-tight bg-gradient-to-r from-teal-400 to-amber-400 bg-clip-text text-transparent m-0 p-0 line-height-none">
                HIFADHI
              </h1>
              <span className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold block -mt-1">
                Alternative Trust Scoring
              </span>
            </div>
          </div>

          {/* Connection controls */}
          <div className="flex items-center gap-4">
            {/* Live API Health Status */}
            <div className="hidden sm:flex items-center gap-2 text-xs">
              <span className="text-slate-500">Local Service:</span>
              <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-900 border border-slate-800 rounded-lg">
                <div className={`w-2 h-2 rounded-full ${apiOnline ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                <span className="font-semibold text-slate-350">{apiOnline ? 'Online' : 'Offline'}</span>
              </div>
            </div>

            {/* Sandbox Toggle */}
            <div className="flex items-center bg-slate-900 border border-slate-800 p-0.5 rounded-lg text-xs font-semibold">
              <button
                onClick={() => handleToggleMock(false)}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md transition-all ${
                  !mockMode 
                    ? 'bg-gradient-to-r from-teal-600 to-teal-500 text-slate-100 shadow' 
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                Live API
              </button>
              <button
                onClick={() => handleToggleMock(true)}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md transition-all ${
                  mockMode 
                    ? 'bg-gradient-to-r from-amber-600 to-amber-500 text-slate-900 shadow' 
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Zap className="w-3.5 h-3.5" />
                Demo Sandbox
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Workspace Frame */}
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 flex flex-col gap-6">
        
        {statusMessage && (
          <div className="p-4 bg-teal-500/10 text-teal-400 border border-teal-500/20 rounded-xl text-sm font-semibold animate-pulse">
            {statusMessage}
          </div>
        )}

        {/* Tab Selection */}
        {!selectedFarmerId && (
          <div className="flex border-b border-slate-900 text-sm font-bold">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-2 px-5 py-3 border-b-2 transition-all ${
                activeTab === 'dashboard'
                  ? 'border-teal-550 text-teal-400 bg-teal-500/[0.02]'
                  : 'border-transparent text-slate-450 hover:text-slate-200'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              Dashboard Overview
            </button>
            <button
              onClick={() => setActiveTab('farmers')}
              className={`flex items-center gap-2 px-5 py-3 border-b-2 transition-all ${
                activeTab === 'farmers'
                  ? 'border-teal-550 text-teal-400 bg-teal-500/[0.02]'
                  : 'border-transparent text-slate-450 hover:text-slate-200'
              }`}
            >
              <Users className="w-4 h-4" />
              Farmer Applications
            </button>
            <button
              onClick={() => setActiveTab('testifiers')}
              className={`flex items-center gap-2 px-5 py-3 border-b-2 transition-all ${
                activeTab === 'testifiers'
                  ? 'border-teal-550 text-teal-400 bg-teal-500/[0.02]'
                  : 'border-transparent text-slate-450 hover:text-slate-200'
              }`}
            >
              <Award className="w-4 h-4" />
              Testifier Audits
            </button>
          </div>
        )}

        {/* Main Content Area */}
        <main className="flex-1">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-4 text-slate-550 animate-pulse">
              <RefreshCw className="w-10 h-10 animate-spin text-teal-400" />
              <span>Fetching alternate credit bureau logs...</span>
            </div>
          ) : selectedFarmerId ? (
            <FarmerDetail 
              farmerId={selectedFarmerId} 
              onBack={() => setSelectedFarmerId(null)}
            />
          ) : (
            <>
              {activeTab === 'dashboard' && (
                <Dashboard 
                  farmers={farmers} 
                  results={results} 
                  onSelectFarmer={setSelectedFarmerId}
                />
              )}
              {activeTab === 'farmers' && (
                <FarmerList 
                  farmers={farmers} 
                  results={results} 
                  onSelectFarmer={setSelectedFarmerId}
                  onStartVerification={handleStartVerification}
                />
              )}
              {activeTab === 'testifiers' && (
                <TestifiersView />
              )}
            </>
          )}
        </main>
      </div>

      {/* Premium Dark Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500 flex flex-col sm:flex-row justify-between items-center max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 gap-3">
        <div>
          &copy; 2026 Hifadhi Credit Scoring System &bull; Mercy Corps AgriFin Brief
        </div>
        <div className="flex items-center gap-1.5">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
          <span>Vouching networks are dynamically monitored. Vouch responsibly.</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
