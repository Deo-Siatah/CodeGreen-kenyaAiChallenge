import React, { useState, useEffect } from 'react';
import { ShieldCheck, AlertTriangle, Scale, RefreshCw, Users, ShieldAlert } from 'lucide-react';
import { type Testifier, api } from '../services/api';

export const TestifiersView: React.FC = () => {
  const [testifiers, setTestifiers] = useState<Testifier[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await api.getTestifiers();
      setTestifiers(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 text-slate-400 animate-pulse">
        <RefreshCw className="w-10 h-10 animate-spin text-teal-400" />
        <span>Loading verifier credibility audits...</span>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-6 animate-fade-in">
      <div>
        <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-teal-400" />
          Testifier Credibility & Reputation Control
        </h3>
        <p className="text-slate-400 text-sm mt-1">
          Monitor community verifier (Chiefs, Elders, Agrovets) vouching accuracy. Vouched cohorts with elevated default rates automatically trigger trust weight discounts to protect the portfolio.
        </p>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="p-4 bg-slate-950 rounded-xl border border-slate-850 flex items-center gap-3">
          <div className="p-2.5 bg-teal-500/10 text-teal-400 rounded-lg border border-teal-500/20">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <span className="block text-[10px] text-slate-500 uppercase font-semibold">Audited Verifiers</span>
            <strong className="text-lg font-extrabold text-slate-200">{testifiers.length}</strong>
          </div>
        </div>

        <div className="p-4 bg-slate-950 rounded-xl border border-slate-850 flex items-center gap-3">
          <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-lg border border-amber-500/20">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <span className="block text-[10px] text-slate-500 uppercase font-semibold">Average Vouching Accuracy</span>
            <strong className="text-lg font-extrabold text-slate-200">93.2%</strong>
          </div>
        </div>

        <div className="p-4 bg-slate-950 rounded-xl border border-slate-850 flex items-center gap-3">
          <div className="p-2.5 bg-rose-500/10 text-rose-400 rounded-lg border border-rose-500/20">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <span className="block text-[10px] text-slate-500 uppercase font-semibold">Flagged / Discounted Verifiers</span>
            <strong className="text-lg font-extrabold text-rose-400">2</strong>
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="min-w-full divide-y divide-slate-800">
          <thead className="bg-slate-950">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Verifier Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Category & Location</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Assessed Cohort</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Vouched Default Rate</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Credibility Score</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Scoring Weight Multiplier</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-900/40">
            {testifiers.map(t => {
              const isFlagged = t.default_rate >= 10.0;
              const isHighRisk = t.default_rate >= 20.0;

              // Credibility colors
              let scoreColor = 'text-emerald-400 font-bold';
              if (t.credibility_score < 50) scoreColor = 'text-rose-400 font-bold';
              else if (t.credibility_score < 80) scoreColor = 'text-amber-400 font-medium';

              return (
                <tr 
                  key={t.id} 
                  className={`transition-colors duration-150 ${
                    isHighRisk ? 'hover:bg-rose-500/5 bg-rose-500/[0.02]' : 
                    isFlagged ? 'hover:bg-amber-500/5 bg-amber-500/[0.01]' : 
                    'hover:bg-slate-800/30'
                  }`}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2.5">
                      <div className="text-sm font-semibold text-slate-200">{t.name}</div>
                      {isHighRisk && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30 uppercase tracking-wider">
                          Critical Alert
                        </span>
                      )}
                      {!isHighRisk && isFlagged && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 uppercase tracking-wider">
                          Discounted
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] font-mono text-slate-550">ID: {t.id}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-350">
                    <div className="text-xs font-semibold text-slate-300">{t.category}</div>
                    <div className="text-xs text-slate-500">{t.location}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300 font-semibold">
                    {t.vouched_count} farmers
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-bold ${
                        isHighRisk ? 'text-rose-400' :
                        isFlagged ? 'text-amber-400' :
                        'text-emerald-400'
                      }`}>
                        {t.default_rate}%
                      </span>
                      {isFlagged && <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />}
                    </div>
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm ${scoreColor}`}>
                    {t.credibility_score}/100
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <Scale className="w-3.5 h-3.5 text-slate-550" />
                      <span className={`text-sm font-bold ${isFlagged ? 'text-amber-400' : 'text-teal-400'}`}>
                        {t.current_weight.toFixed(1)}x
                      </span>
                      {isFlagged && (
                        <span className="text-[10px] text-slate-500 line-through font-semibold">
                          ({t.category === 'Chief' || t.category === 'Buyer' ? '4.0' : '3.0'}x)
                        </span>
                      )}
                    </div>
                    {isFlagged && (
                      <span className="block text-[9px] text-amber-500/80 font-medium">
                        Reputation discount applied
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
