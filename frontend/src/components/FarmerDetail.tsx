import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, AlertTriangle, CheckCircle2, 
  Activity, User, RefreshCw, BrainCircuit, Globe 
} from 'lucide-react';
import { type Farmer, type FinalResult, type VerificationLog, api } from '../services/api';

interface FarmerDetailProps {
  farmerId: string;
  onBack: () => void;
}

export const FarmerDetail: React.FC<FarmerDetailProps> = ({ farmerId, onBack }) => {
  const [farmer, setFarmer] = useState<Farmer | null>(null);
  const [result, setResult] = useState<FinalResult | null>(null);
  const [logs, setLogs] = useState<VerificationLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [language, setLanguage] = useState<'en' | 'sw'>('en');
  const [actionStatus, setActionStatus] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const f = await api.getFarmer(farmerId);
      const res = await api.getVerificationResult(farmerId);
      setFarmer(f);
      setResult(res);

      if (res) {
        const l = await api.getLogs(res.session_id, farmerId);
        setLogs(l);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [farmerId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 text-slate-400">
        <RefreshCw className="w-10 h-10 animate-spin text-teal-400" />
        <span>Loading alternative credit score details...</span>
      </div>
    );
  }

  if (!farmer) {
    return (
      <div className="text-center py-20 text-slate-400">
        <span>Farmer profile not found.</span>
        <button onClick={onBack} className="block mx-auto mt-4 px-4 py-2 bg-slate-800 text-slate-200 rounded-lg">
          Back to List
        </button>
      </div>
    );
  }

  // Simulations
  const handleSimulateTimeout = async (phone: string) => {
    if (!result) return;
    setSimulating(true);
    try {
      // Direct call or mock simulation
      if (api.isMockMode()) {
        // Mock timeout logic
        const updatedResult = { ...result };
        const participant = updatedResult.participant_scores.find(p => p.phone === phone);
        if (participant) {
          participant.status = 'timeout' as const;
          participant.raw_score = 0;
          participant.weighted_score = 0;
        }
        // Recalculate trust score
        let totalWeighted = 0;
        let totalWeight = 0;
        updatedResult.participant_scores.forEach(p => {
          totalWeight += p.weight;
          if (p.status === 'received') {
            totalWeighted += p.raw_score * p.weight;
          }
        });
        updatedResult.trust_score = totalWeight > 0 ? Math.round((totalWeighted / totalWeight) * 100) / 100 : 0;
        updatedResult.decision = 'REVIEW_REQUIRED';
        updatedResult.recommendation = 'REVIEW';
        updatedResult.analysis = {
          summary: 'Assessment update: Verifier timed out.',
          explanation: 'The verification score was recalculated after a participant failed to respond within the required window.',
          key_drivers: updatedResult.analysis.key_drivers,
          risk_factors: [...updatedResult.analysis.risk_factors, `${participant?.participant_type} failed to respond (vouching timeout penalty).`]
        };
        
        // Add log entry
        const logEntry: VerificationLog = {
          timestamp: new Date().toISOString(),
          event: 'PARTICIPANT_TIMEOUT',
          participant: participant?.participant_type,
          phone,
          details: { reason: 'Manual demo timeout simulation' }
        };
        
        setLogs(prev => [...prev, logEntry]);
        setResult(updatedResult);
      } else {
        // Call backend simulate timeout endpoint
        const res = await fetch(`http://localhost:8000/api/verify/${result.session_id}/simulate-timeout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone })
        });
        if (res.ok) {
          await loadData();
        }
      }
    } catch (e) {
      alert('Error simulating timeout');
    } finally {
      setSimulating(false);
    }
  };

  const handleSimulateResponse = async (phone: string, answers: string[]) => {
    if (!result) return;
    setSimulating(true);
    try {
      if (api.isMockMode()) {
        const updatedResult = { ...result };
        const participant = updatedResult.participant_scores.find(p => p.phone === phone);
        if (participant) {
          participant.status = 'received' as const;
          participant.responses = answers.map((ans, idx) => ({ question_id: `Q${idx}`, answer: ans }));
          // YES = 100, UNSURE = 50, NO = 0
          const totalPoints = answers.reduce((sum, ans) => {
            if (ans === 'YES') return sum + 100;
            if (ans === 'UNSURE') return sum + 50;
            return sum;
          }, 0);
          participant.raw_score = Math.round((totalPoints / answers.length) * 100) / 100;
          participant.weighted_score = participant.raw_score * participant.weight;
        }

        // Check if all complete
        const allComplete = updatedResult.participant_scores.every(p => p.status !== 'pending');
        if (allComplete) {
          updatedResult.status = 'complete';
          updatedResult.completed_at = new Date().toISOString();
          
          let totalWeighted = 0;
          let totalWeight = 0;
          updatedResult.participant_scores.forEach(p => {
            totalWeight += p.weight;
            if (p.status === 'received') {
              totalWeighted += p.raw_score * p.weight;
            }
          });
          
          updatedResult.trust_score = totalWeight > 0 ? Math.round((totalWeighted / totalWeight) * 100) / 100 : 0;
          if (updatedResult.trust_score >= 75) {
            updatedResult.decision = 'ELIGIBLE';
            updatedResult.recommendation = 'APPROVE_LEVEL_2';
            updatedResult.loan_amount_recommended_kes = 5000;
          } else if (updatedResult.trust_score >= 60) {
            updatedResult.decision = 'ELIGIBLE';
            updatedResult.recommendation = 'APPROVE_LEVEL_1';
            updatedResult.loan_amount_recommended_kes = 3000;
          } else {
            updatedResult.decision = 'DECLINE';
            updatedResult.recommendation = 'DECLINE';
          }
        }

        const logEntry: VerificationLog = {
          timestamp: new Date().toISOString(),
          event: 'RESPONSE_RECEIVED',
          participant: participant?.participant_type,
          phone,
          details: { answers }
        };
        
        setLogs(prev => [...prev, logEntry]);
        setResult(updatedResult);
      } else {
        // Simulate submitting responses one by one through backend
        for (let i = 0; i < answers.length; i++) {
          await fetch(`http://localhost:8000/api/ussd/respond`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              phone,
              session_id: result.session_id,
              answer: answers[i]
            })
          });
        }
        await loadData();
      }
    } catch (e) {
      alert('Error simulating response');
    } finally {
      setSimulating(false);
    }
  };

  const handleAction = (type: string) => {
    setActionStatus(`Application status updated: ${type}`);
    setTimeout(() => setActionStatus(null), 3000);
  };

  // Vouching weight math summary
  const totalWeight = result?.participant_scores.reduce((sum, p) => sum + p.weight, 0) || 0;

  // Kiswahili translation translations
  const swahiliAnalysis = {
    summary: 'Uthibitisho thabiti wa kijamii na uhusiano mzuri wa kibiashara.',
    explanation: `Mkulima alipata alama ya uaminifu ya ${result?.trust_score || 0}/100. Chifu alithibitisha tabia nzuri ya mkulima na mipango ya shamba. Ununuzi wa pembejeo za kilimo ni wa kiwango cha kuridhisha na mauzo ya ndizi yanaonyesha rekodi nzuri ya mapato.`,
    key_drivers: [
      'Chifu alitoa uthibitisho mzuri sana wa uaminifu.',
      'Mnunuzi alithibitisha mauzo thabiti ya mazao kila msimu.',
      'Mwanachama hai wa Mwea SACCO mwenye akiba ya kutosha.'
    ],
    risk_factors: [
      'Muuzaji wa pembejeo alionyesha kulikuwa na ucheleweshaji mdogo wa malipo hapo awali.'
    ]
  };

  const activeAnalysis = language === 'sw' ? swahiliAnalysis : result?.analysis;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back Button / Actions */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <button 
          onClick={onBack} 
          className="flex items-center gap-2 text-sm font-semibold text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Farmer Applications
        </button>
        <div className="flex gap-2 w-full sm:w-auto">
          <button 
            onClick={() => setLanguage(l => l === 'en' ? 'sw' : 'en')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition-all shadow-sm"
          >
            <Globe className="w-3.5 h-3.5" />
            {language === 'en' ? 'Tafsiri Kiswahili' : 'Show English'}
          </button>
          <button 
            onClick={loadData} 
            className="flex items-center gap-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition-all shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {actionStatus && (
        <div className="p-4 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-xl text-sm font-semibold animate-pulse">
          {actionStatus}
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Hand Column: Farmer Bio and Signal Breakdown */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Farmer Bio Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
            <div className="flex items-start gap-4">
              <div className="p-3.5 bg-slate-800 rounded-xl border border-slate-750 text-teal-400">
                <User className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xl font-bold text-slate-100">{farmer.full_name}</h3>
                <p className="text-sm text-slate-400">{farmer.farming_type} &bull; {farmer.location}</p>
                <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-slate-500 pt-2">
                  <span>Phone: <strong className="text-slate-350">{farmer.phone}</strong></span>
                  <span>Age: <strong className="text-slate-350">{farmer.age}</strong></span>
                  <span>Gender: <strong className="text-slate-350">{farmer.gender}</strong></span>
                  {farmer.years_farming && (
                    <span>Years Farming: <strong className="text-slate-350">{farmer.years_farming}</strong></span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Traceable Vouching Breakdowns */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
            <div>
              <h4 className="text-lg font-bold text-slate-200">Alternative Vouching Verification Math</h4>
              <p className="text-slate-400 text-xs mt-1">
                Lenders verify decisions by looking at each contributor's response raw score and weight multiplier.
              </p>
            </div>

            {/* Math Explanation Alert */}
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-850 text-slate-400 text-xs flex items-start gap-2.5">
              <Activity className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
              <div>
                <strong>Score Formulation:</strong> Trust Score = <code>sum(Raw Score &times; Weight) &divide; sum(Weight)</code>. 
                Timeouts contribute <code>0</code> points but retain their denominator weight, representing a lack of local community trust.
              </div>
            </div>

            {result ? (
              <div className="space-y-4">
                {result.participant_scores.map((p, idx) => {
                  const contributionPct = totalWeight > 0 ? Math.round((p.weight / totalWeight) * 100) : 0;
                  const earnedPoints = p.status === 'received' ? p.raw_score : 0;
                  const contribPoints = totalWeight > 0 ? Math.round((earnedPoints * p.weight) / totalWeight) : 0;

                  return (
                    <div key={idx} className="p-4 bg-slate-950 rounded-xl border border-slate-850 space-y-3">
                      <div className="flex justify-between items-start gap-2">
                        <div>
                          <span className="text-xs font-semibold tracking-wider text-teal-400 uppercase bg-teal-500/5 px-2 py-0.5 rounded border border-teal-500/10">
                            {p.participant_type}
                          </span>
                          <h5 className="text-sm font-bold text-slate-200 mt-1.5">{p.participant_name}</h5>
                          <span className="text-xs text-slate-500">{p.phone}</span>
                        </div>
                        <div className="text-right">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold ${
                            p.status === 'received' ? 'bg-emerald-500/10 text-emerald-400' :
                            p.status === 'pending' ? 'bg-amber-500/10 text-amber-500 animate-pulse' :
                            'bg-rose-500/10 text-rose-400'
                          }`}>
                            {p.status.toUpperCase()}
                          </span>
                          <div className="text-xs text-slate-400 mt-1 font-semibold">
                            {p.status === 'received' ? `Raw Score: ${p.raw_score}/100` : 'Score Contribution: 0/100'}
                          </div>
                        </div>
                      </div>

                      {/* Math breakout breakdown */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2 border-t border-slate-900 text-xs text-slate-400">
                        <div>
                          <span className="block text-[10px] uppercase text-slate-500">Weight Multiplier</span>
                          <strong className="text-slate-300 font-bold">{p.weight}x</strong>
                        </div>
                        <div>
                          <span className="block text-[10px] uppercase text-slate-500">Portfolio Weight</span>
                          <strong className="text-slate-300">{contributionPct}% share</strong>
                        </div>
                        <div>
                          <span className="block text-[10px] uppercase text-slate-500">Contribution Formula</span>
                          <code className="text-slate-300 font-mono">
                            {p.status === 'received' ? `(${p.raw_score} &times; ${p.weight})` : `(0 &times; ${p.weight})`}
                          </code>
                        </div>
                        <div className="text-right">
                          <span className="block text-[10px] uppercase text-slate-500">Final Impact</span>
                          <strong className="text-teal-400">+{contribPoints} pts to Score</strong>
                        </div>
                      </div>

                      {/* Responses Sub-panel */}
                      {p.status === 'received' && p.responses.length > 0 && (
                        <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-900 space-y-1.5">
                          <span className="block text-[10px] uppercase text-slate-500 font-semibold mb-1">SMS Verification Answers:</span>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                            {p.responses.map((resp, rid) => (
                              <div key={rid} className="flex justify-between items-center text-xs bg-slate-950 p-1.5 rounded border border-slate-800">
                                <span className="text-slate-400 font-mono text-[10px]">{resp.question_id}</span>
                                <span className={`font-bold ${resp.answer === 'YES' ? 'text-emerald-400' : resp.answer === 'UNSURE' ? 'text-amber-400' : 'text-rose-400'}`}>
                                  {resp.answer}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Simulation Actions */}
                      {p.status === 'pending' && (
                        <div className="flex gap-2 pt-2 justify-end">
                          <button
                            disabled={simulating}
                            onClick={() => handleSimulateTimeout(p.phone)}
                            className="px-2.5 py-1.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded hover:bg-rose-500/20 text-xs font-semibold transition-colors"
                          >
                            Simulate 48h Timeout
                          </button>
                          <button
                            disabled={simulating}
                            onClick={() => handleSimulateResponse(p.phone, ['YES', 'YES', 'YES'])}
                            className="px-2.5 py-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded hover:bg-emerald-500/20 text-xs font-semibold transition-colors"
                          >
                            Simulate Vouching "YES"
                          </button>
                          <button
                            disabled={simulating}
                            onClick={() => handleSimulateResponse(p.phone, ['YES', 'NO', 'UNSURE'])}
                            className="px-2.5 py-1.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded hover:bg-amber-500/20 text-xs font-semibold transition-colors"
                          >
                            Simulate Mixed Responses
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-6 text-slate-500 text-sm">
                No active alternative credit scoring session found. Click Assess Trust to build a session.
              </div>
            )}
          </div>

          {/* Session Logs / Audit trail */}
          {result && logs.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
              <h4 className="text-lg font-bold text-slate-200">Sandbox Verification Audit Trail</h4>
              <div className="relative border-l-2 border-slate-800 pl-4 space-y-4 max-h-[300px] overflow-y-auto">
                {logs.map((log, i) => (
                  <div key={i} className="relative">
                    <div className="absolute -left-[21px] top-1.5 w-2 h-2 rounded-full bg-teal-400 border border-slate-900"></div>
                    <div className="text-[11px] text-slate-500 font-mono">{new Date(log.timestamp).toLocaleTimeString()}</div>
                    <div className="text-xs font-semibold text-slate-350 mt-0.5">{log.event.replace('_', ' ')}</div>
                    {log.participant && (
                      <div className="text-[10px] text-slate-400">
                        Verifier: {log.participant} ({log.phone})
                      </div>
                    )}
                    {Object.keys(log.details).length > 0 && (
                      <pre className="text-[10px] bg-slate-950 p-1.5 rounded font-mono text-slate-500 mt-1 max-w-full overflow-x-auto">
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Hand Column: Score Display & AI Explainability */}
        <div className="space-y-6">
          
          {/* Radial score / badge */}
          {result ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm text-center space-y-5">
              <span className="text-xs font-semibold text-slate-400 tracking-wider uppercase">Alternative Trust Score</span>
              
              <div className="relative w-36 h-36 mx-auto flex items-center justify-center">
                {/* SVG Radial Gauge */}
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" className="stroke-slate-800 fill-none" strokeWidth="8" />
                  <circle 
                    cx="50" 
                    cy="50" 
                    r="40" 
                    className="stroke-teal-500 fill-none transition-all duration-1000 ease-out" 
                    strokeWidth="8" 
                    strokeDasharray="251.2"
                    strokeDashoffset={251.2 - (251.2 * result.trust_score) / 100}
                  />
                </svg>
                <div className="absolute text-center">
                  <span className="text-4xl font-extrabold text-slate-100">{Math.round(result.trust_score)}</span>
                  <span className="block text-slate-400 text-xs">/100</span>
                </div>
              </div>

              {/* Status Band badge */}
              <div className="space-y-1">
                <span className={`inline-flex px-3 py-1 rounded-full text-xs font-bold ${
                  result.decision === 'ELIGIBLE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                  result.decision === 'REVIEW_REQUIRED' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                  'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                }`}>
                  {result.decision === 'ELIGIBLE' ? 'ELIGIBLE CREDIT BAND' :
                   result.decision === 'REVIEW_REQUIRED' ? 'MANUAL REVIEW REQUIRED' : 'DECLINE'}
                </span>
                
                {result.loan_amount_recommended_kes ? (
                  <div className="text-sm font-bold text-amber-400 mt-2">
                    Recommended Voucher: KES {result.loan_amount_recommended_kes.toLocaleString()}
                  </div>
                ) : (
                  <div className="text-xs text-slate-500 mt-1">No automatic credit vouchers recommended.</div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm text-center py-10 text-slate-500">
              Awaiting assessment session.
            </div>
          )}

          {/* AI Explainability view */}
          {result && activeAnalysis && (
            <div className="bg-gradient-to-b from-slate-900 to-slate-950 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <BrainCircuit className="w-5 h-5 text-amber-500" />
                <h4 className="text-md font-bold text-slate-200">Gemini Credit Explanation</h4>
              </div>

              <div className="space-y-3.5">
                <div className="text-xs italic text-slate-400 bg-slate-900 p-3 rounded-lg border border-slate-850">
                  &ldquo;{activeAnalysis.summary}&rdquo;
                </div>

                <div className="text-xs text-slate-350 leading-relaxed font-medium">
                  {activeAnalysis.explanation}
                </div>

                {/* Key Drivers */}
                <div className="space-y-2 pt-2">
                  <span className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider">Key Vouching Strengths</span>
                  <div className="space-y-1.5">
                    {activeAnalysis.key_drivers.map((drv, i) => (
                      <div key={i} className="flex gap-2 text-xs text-emerald-400">
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                        <span>{drv}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Risk Factors */}
                {activeAnalysis.risk_factors && activeAnalysis.risk_factors.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <span className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider">Flagged Risk Adjustments</span>
                    <div className="space-y-1.5">
                      {activeAnalysis.risk_factors.map((risk, i) => (
                        <div key={i} className="flex gap-2 text-xs text-amber-400">
                          <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                          <span>{risk}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Action buttons */}
          {result && result.status !== 'pending' && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-3">
              <button
                onClick={() => handleAction('Approved & Voucher Issued')}
                className="w-full py-2.5 bg-gradient-to-r from-emerald-600 to-emerald-500 text-slate-100 rounded-xl hover:from-emerald-500 hover:to-emerald-400 text-sm font-bold shadow-md hover:scale-[1.01] transition-all"
              >
                Approve & Issue Voucher
              </button>
              <button
                onClick={() => handleAction('Information Request Triggered')}
                className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-bold border border-slate-700 transition-all"
              >
                Request More Information (SMS)
              </button>
              <button
                onClick={() => handleAction('Credit Application Declined')}
                className="w-full py-2.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 rounded-xl text-xs font-bold border border-rose-500/20 transition-all"
              >
                Decline & Refer to Training
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
