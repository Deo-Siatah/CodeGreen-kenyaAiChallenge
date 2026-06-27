import React, { useState } from 'react';
import { Search, Filter, AlertCircle, Plus } from 'lucide-react';
import type { Farmer, FinalResult } from '../services/api';

interface FarmerListProps {
  farmers: Farmer[];
  results: Record<string, FinalResult>;
  onSelectFarmer: (id: string) => void;
  onStartVerification: (id: string) => void;
}

export const FarmerList: React.FC<FarmerListProps> = ({ 
  farmers, 
  results, 
  onSelectFarmer,
  onStartVerification
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [locationFilter, setLocationFilter] = useState('ALL');

  // Locations list for filter dropdown
  const locations = Array.from(new Set(farmers.map(f => f.location)));

  // Filter calculations
  const filteredFarmers = farmers.filter(f => {
    const matchesSearch = f.full_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          f.phone.includes(searchTerm);
    
    const result = results[f.id];
    const rec = result ? result.recommendation : 'NEEDS_VERIFICATION';

    let matchesStatus = true;
    if (statusFilter !== 'ALL') {
      if (statusFilter === 'APPROVED') {
        matchesStatus = rec === 'APPROVE_LEVEL_1' || rec === 'APPROVE_LEVEL_2';
      } else if (statusFilter === 'REVIEW') {
        matchesStatus = rec === 'REVIEW' || result?.decision === 'REVIEW_REQUIRED';
      } else if (statusFilter === 'DECLINED') {
        matchesStatus = rec === 'DECLINE';
      } else if (statusFilter === 'PENDING') {
        matchesStatus = rec === 'NEEDS_VERIFICATION' || result?.status === 'pending';
      }
    }

    const matchesLocation = locationFilter === 'ALL' || f.location === locationFilter;

    return matchesSearch && matchesStatus && matchesLocation;
  });

  // Get score tier badge and colors
  const getScoreBadge = (result?: FinalResult) => {
    if (!result) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
          Unassessed
        </span>
      );
    }

    const score = result.trust_score;
    if (score >= 75) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          Tier 1 (High Trust) &mdash; {score}
        </span>
      );
    } else if (score >= 60) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20">
          Tier 2 (Good Trust) &mdash; {score}
        </span>
      );
    } else if (score >= 45) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          Tier 3 (Review Pathway) &mdash; {score}
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
          Tier 4 (Low Trust) &mdash; {score}
        </span>
      );
    }
  };

  // Get recommendation label
  const getRecommendationLabel = (result?: FinalResult) => {
    if (!result) return 'Start Verification';
    
    if (result.status === 'pending') {
      return 'Verification Pending';
    }

    const rec = result.recommendation;
    switch (rec) {
      case 'APPROVE_LEVEL_2':
        return 'Approved (KES 5,000)';
      case 'APPROVE_LEVEL_1':
        return 'Approved (KES 3,000)';
      case 'REVIEW':
        return 'Manual Review / Chama';
      case 'DECLINE':
        return 'Training Pathway';
      default:
        return 'Review Recommended';
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-6 animate-fade-in">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h3 className="text-xl font-bold text-slate-100">Farmer Verification Profiles</h3>
          <p className="text-slate-400 text-sm mt-1">Review active, completed, and pending farmer alternative credit assessments.</p>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-slate-950 rounded-xl border border-slate-850">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4.5 w-4.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search by name or phone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-700/80 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500 transition-colors"
          />
        </div>

        {/* Filter Status */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400 shrink-0" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-teal-500 transition-colors cursor-pointer"
          >
            <option value="ALL">All Decision Statuses</option>
            <option value="APPROVED">Approved (Level 1 & 2)</option>
            <option value="REVIEW">Under Review / Timeout</option>
            <option value="DECLINED">Training Pathway (Declined)</option>
            <option value="PENDING">Awaiting Responses</option>
          </select>
        </div>

        {/* Filter Location */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400 shrink-0" />
          <select
            value={locationFilter}
            onChange={(e) => setLocationFilter(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-teal-500 transition-colors cursor-pointer"
          >
            <option value="ALL">All Locations</option>
            {locations.map(loc => (
              <option key={loc} value={loc}>{loc}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Grid of Farmers / Table */}
      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="min-w-full divide-y divide-slate-800">
          <thead className="bg-slate-950">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Farmer Detail</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Farming Activity</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Credit Score & Tier</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Decision Recommendation</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-900/40">
            {filteredFarmers.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-10 text-center text-slate-500 text-sm">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <AlertCircle className="w-8 h-8 text-slate-600" />
                    <span>No farmer profiles match the current filter criteria.</span>
                  </div>
                </td>
              </tr>
            ) : (
              filteredFarmers.map(f => {
                const result = results[f.id];
                const hasResult = !!result;

                return (
                  <tr 
                    key={f.id} 
                    className="hover:bg-slate-800/30 transition-colors duration-150"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div 
                        onClick={() => onSelectFarmer(f.id)}
                        className="text-sm font-semibold text-slate-200 hover:text-teal-400 cursor-pointer transition-colors duration-100"
                      >
                        {f.full_name}
                      </div>
                      <div className="text-xs text-slate-500">{f.phone} | {f.location}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                      <div>{f.farming_type}</div>
                      <div className="text-xs text-slate-500">Reg: {f.registration_date ? new Date(f.registration_date).toLocaleDateString() : 'N/A'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getScoreBadge(result)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                        !hasResult ? 'bg-slate-800 text-slate-400 border border-slate-700' :
                        result.status === 'pending' ? 'bg-amber-500/10 text-amber-500 border border-amber-500/25 animate-pulse' :
                        result.recommendation === 'APPROVE_LEVEL_2' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        result.recommendation === 'APPROVE_LEVEL_1' ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20' :
                        result.recommendation === 'REVIEW' || result.decision === 'REVIEW_REQUIRED' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                        'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {getRecommendationLabel(result)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      {hasResult ? (
                        <button
                          onClick={() => onSelectFarmer(f.id)}
                          className="px-3 py-1.5 bg-gradient-to-r from-teal-600 to-teal-500 text-slate-100 rounded-lg hover:from-teal-500 hover:to-teal-400 transition-colors shadow-sm text-xs font-semibold"
                        >
                          View Breakdown
                        </button>
                      ) : (
                        <button
                          onClick={() => onStartVerification(f.id)}
                          className="px-3 py-1.5 bg-gradient-to-r from-amber-600 to-amber-500 text-slate-900 rounded-lg hover:from-amber-500 hover:to-amber-400 transition-colors shadow-sm text-xs font-semibold flex items-center gap-1 ml-auto"
                        >
                          <Plus className="w-3.5 h-3.5 stroke-[3]" />
                          Assess Trust
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
