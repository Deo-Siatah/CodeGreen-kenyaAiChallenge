import React from 'react';
import { Users, CheckCircle, Scale, Clock, Award, TrendingUp, ShieldCheck } from 'lucide-react';
import type { Farmer, FinalResult } from '../services/api';

interface DashboardProps {
  farmers: Farmer[];
  results: Record<string, FinalResult>;
  onSelectFarmer: (id: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ farmers, results, onSelectFarmer }) => {
  // Compute metrics from actual data
  const totalAssessed = farmers.length;
  
  const eligibleResults = Object.values(results).filter(r => r.decision === 'ELIGIBLE');
  const approvalRate = totalAssessed > 0 
    ? Math.round((eligibleResults.length / totalAssessed) * 100) 
    : 0;

  const loans = Object.values(results)
    .map(r => r.loan_amount_recommended_kes)
    .filter((amt): amt is number => typeof amt === 'number' && amt > 0);
  
  const avgLoanSize = loans.length > 0
    ? Math.round(loans.reduce((sum, val) => sum + val, 0) / loans.length)
    : 0;

  // Average repayment rate: Mocked from local branch history (e.g. 96.8%) since it is a branch-level portfolio metric
  const repaymentRate = 97.4; 

  const pendingCount = Object.values(results).filter(
    r => r.status === 'pending' || r.decision === 'REVIEW_REQUIRED'
  ).length;

  // Key stats definition
  const stats = [
    {
      title: 'Total Farmers Assessed',
      value: totalAssessed.toString(),
      change: '+12% this month',
      icon: Users,
      color: 'from-slate-700 to-slate-800',
      textColor: 'text-teal-400'
    },
    {
      title: 'Vouching Approval Rate',
      value: `${approvalRate}%`,
      change: 'Healthy benchmark (70%+)',
      icon: CheckCircle,
      color: 'from-teal-700 to-teal-800',
      textColor: 'text-amber-400'
    },
    {
      title: 'Average Loan Size',
      value: `KES ${avgLoanSize.toLocaleString()}`,
      change: 'Based on approved vouchers',
      icon: Scale,
      color: 'from-slate-800 to-slate-900',
      textColor: 'text-teal-300'
    },
    {
      title: 'Portfolio Repayment Rate',
      value: `${repaymentRate}%`,
      change: '0.4% improvement QoQ',
      icon: TrendingUp,
      color: 'from-teal-800 to-slate-900',
      textColor: 'text-emerald-400'
    },
    {
      title: 'Pending Decisions',
      value: pendingCount.toString(),
      change: 'Requires immediate action',
      icon: Clock,
      color: 'from-amber-800 to-amber-950',
      textColor: 'text-amber-300'
    }
  ];

  // Group by crop type for a quick distribution metric
  const cropDistribution = farmers.reduce((acc, f) => {
    const crop = f.farming_type.split(' ')[0] || 'Other';
    acc[crop] = (acc[crop] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-gradient-to-r from-slate-900 via-slate-800 to-teal-905 rounded-2xl border border-slate-700/50 shadow-xl">
        <div>
          <h2 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-7 h-7 text-amber-500" />
            Branch Credit Portfolio Control
          </h2>
          <p className="text-slate-300 text-sm mt-1">
            SACCO Loan Officer Desk &mdash; Alternative Social Trust Credit Scoring Engine.
          </p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/80 rounded-xl border border-slate-700">
          <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-ping"></div>
          <span className="text-xs font-semibold text-slate-200">System Connected</span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-5">
        {stats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div
              key={i}
              className={`p-5 rounded-2xl bg-gradient-to-br ${stat.color} border border-slate-700/50 hover:border-slate-500/30 transition-all duration-300 shadow-md flex flex-col justify-between group cursor-default`}
            >
              <div className="flex justify-between items-start">
                <span className="text-xs font-medium text-slate-400 tracking-wider uppercase">{stat.title}</span>
                <Icon className={`w-5 h-5 ${stat.textColor} opacity-80 group-hover:scale-110 transition-transform`} />
              </div>
              <div className="mt-4">
                <span className={`text-3xl font-extrabold tracking-tight ${stat.textColor}`}>
                  {stat.value}
                </span>
                <span className="block text-[11px] text-slate-400 mt-2 font-medium">
                  {stat.change}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Applications Feed */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <h3 className="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2">
            <Award className="w-5 h-5 text-amber-500" />
            Recent Assessment Activity
          </h3>
          <div className="overflow-hidden rounded-xl border border-slate-800">
            <table className="min-w-full divide-y divide-slate-800">
              <thead className="bg-slate-950">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Farmer</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Activity</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Trust Score</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Recommendation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-slate-900/50">
                {farmers.slice(0, 4).map(f => {
                  const result = results[f.id];
                  const hasResult = !!result;
                  const score = hasResult ? result.trust_score : 'Not Assessed';
                  const rec = hasResult ? result.recommendation : 'Needs Verification';
                  
                  // Score color class
                  let scoreColor = 'text-slate-400';
                  if (hasResult) {
                    if (result.trust_score >= 75) scoreColor = 'text-emerald-400 font-bold';
                    else if (result.trust_score >= 60) scoreColor = 'text-teal-400 font-medium';
                    else if (result.trust_score >= 45) scoreColor = 'text-amber-400 font-medium';
                    else scoreColor = 'text-rose-400 font-bold';
                  }

                  return (
                    <tr 
                      key={f.id} 
                      onClick={() => onSelectFarmer(f.id)}
                      className="hover:bg-slate-800/40 cursor-pointer transition-colors duration-150"
                    >
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <div className="text-sm font-semibold text-slate-200">{f.full_name}</div>
                        <div className="text-xs text-slate-500">{f.location}</div>
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap text-sm text-slate-300">
                        {f.farming_type}
                      </td>
                      <td className={`px-4 py-3.5 whitespace-nowrap text-sm ${scoreColor}`}>
                        {hasResult ? `${score}/100` : score}
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                          rec === 'APPROVE_LEVEL_2' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                          rec === 'APPROVE_LEVEL_1' ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20' :
                          rec === 'REVIEW' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                          rec === 'DECLINE' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                          'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                        }`}>
                          {rec.replace('_', ' ')}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Portfolio Distribution */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col">
          <h3 className="text-lg font-bold text-slate-200 mb-4">
            Crop Portfolio Share
          </h3>
          <div className="flex-1 flex flex-col justify-center space-y-4">
            {Object.entries(cropDistribution).map(([crop, count]) => {
              const percentage = Math.round((count / totalAssessed) * 100);
              return (
                <div key={crop} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-300">{crop} Farming</span>
                    <span className="text-slate-400">{count} ({percentage}%)</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2">
                    <div 
                      className="bg-gradient-to-r from-teal-500 to-amber-500 h-2 rounded-full" 
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
