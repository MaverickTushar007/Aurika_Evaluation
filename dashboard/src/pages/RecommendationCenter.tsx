import React, { useState } from 'react';
import { useWorldStore } from '../state/useWorldStore';
import { useAuthStore } from '../state/useAuthStore';
import {
  Sparkles,
  CheckCircle2,
  Filter,
  Search,
  ArrowUpRight,
  TrendingUp,
  SlidersHorizontal,
} from 'lucide-react';

export const RecommendationCenter: React.FC = () => {
  const { recommendations, acknowledgeRecommendation } = useWorldStore();
  const { hasPermission } = useAuthStore();
  const [filterPriority, setFilterPriority] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const canAct = hasPermission(['Operator', 'Administrator']);

  const filteredRecs = recommendations.filter((rec) => {
    if (filterPriority !== 'ALL' && rec.priority !== filterPriority) return false;
    if (searchQuery && !rec.title.toLowerCase().includes(searchQuery.toLowerCase()) && !rec.reason.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>Decision & Optimization Engine (DOE) Center</span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-normal">
              Operations Research
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Review, audit, and execute ranked operational interventions proposed by the intelligence layer.
          </p>
        </div>
      </div>

      {/* Search & Filter Controls */}
      <div className="glass-panel p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
          <input
            type="text"
            placeholder="Search recommendations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto">
          <Filter className="w-4 h-4 text-slate-400 flex-shrink-0" />
          {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((p) => (
            <button
              key={p}
              onClick={() => setFilterPriority(p)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition-all ${
                filterPriority === p
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-white'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Recommendations List */}
      <div className="space-y-4">
        {filteredRecs.map((rec) => (
          <div
            key={rec.id}
            className={`glass-panel p-6 border-l-4 transition-all ${
              rec.acknowledged ? 'border-l-slate-600 opacity-60' :
              rec.priority === 'HIGH' ? 'border-l-rose-500 shadow-lg shadow-rose-950/10' :
              rec.priority === 'MEDIUM' ? 'border-l-amber-500' : 'border-l-blue-500'
            }`}
          >
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
              <div className="space-y-3 flex-1">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className={`px-2.5 py-0.5 text-xs font-bold uppercase rounded ${
                    rec.priority === 'HIGH' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                    rec.priority === 'MEDIUM' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                    'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                  }`}>
                    {rec.priority} PRIORITY
                  </span>
                  <span className="text-xs text-slate-400 font-mono">ID: {rec.id}</span>
                  <span className="text-xs text-emerald-400 font-bold">• Confidence: {Math.round(rec.confidence * 100)}%</span>
                  {rec.acknowledged && (
                    <span className="px-2 py-0.5 text-xs font-bold uppercase rounded bg-slate-800 text-slate-400 border border-slate-700">
                      Acknowledged & Executed
                    </span>
                  )}
                </div>

                <h3 className="text-lg font-bold text-white">{rec.title}</h3>
                <p className="text-sm text-slate-300 leading-relaxed">{rec.reason}</p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5 mb-1">
                      <TrendingUp className="w-4 h-4" />
                      <span>Expected Benefit & Throughput Impact</span>
                    </span>
                    <p className="text-xs text-slate-200 font-medium">{rec.expectedBenefit}</p>
                    <span className="text-[11px] text-slate-400 block mt-1">Impact: {rec.businessImpact}</span>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <span className="text-xs font-semibold text-teal-400 flex items-center gap-1.5 mb-1">
                      <SlidersHorizontal className="w-4 h-4" />
                      <span>Supporting Evidence Trail</span>
                    </span>
                    <ul className="text-xs text-slate-300 space-y-1 list-disc list-inside">
                      {rec.evidence.map((ev, idx) => (
                        <li key={idx} className="truncate">{ev}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              <div className="flex md:flex-col items-center justify-end gap-3 flex-shrink-0">
                {!rec.acknowledged && canAct && (
                  <button
                    onClick={() => acknowledgeRecommendation(rec.id)}
                    className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-900/30 transition-all flex items-center gap-2"
                  >
                    <CheckCircle2 className="w-5 h-5" />
                    <span>Acknowledge Action</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
