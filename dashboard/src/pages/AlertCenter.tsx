import React, { useState } from 'react';
import { useWorldStore } from '../state/useWorldStore';
import {
  ShieldAlert,
  Search,
  Filter,
  CheckCircle2,
  MapPin,
  Clock,
} from 'lucide-react';

export const AlertCenter: React.FC = () => {
  const { alerts } = useWorldStore();
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredAlerts = alerts.filter((alt) => {
    if (filterSeverity !== 'ALL' && alt.severity !== filterSeverity) return false;
    if (searchQuery && !alt.title.toLowerCase().includes(searchQuery.toLowerCase()) && !alt.description.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>System Anomaly & Alert Center</span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30 font-normal">
              Continuous Monitoring
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time event anomalies and sensor triggers across surveillance zones.
          </p>
        </div>
      </div>

      {/* Search & Filter Controls */}
      <div className="glass-panel p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
          <input
            type="text"
            placeholder="Search alerts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:border-rose-500 transition-colors"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto">
          <Filter className="w-4 h-4 text-slate-400 flex-shrink-0" />
          {['ALL', 'CRITICAL', 'WARNING', 'INFO'].map((s) => (
            <button
              key={s}
              onClick={() => setFilterSeverity(s)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition-all ${
                filterSeverity === s
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                  : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-white'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Alerts List */}
      <div className="space-y-3">
        {filteredAlerts.length === 0 ? (
          <div className="glass-panel text-center py-12">
            <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
            <p className="text-sm font-semibold text-white">No alerts found matching your criteria.</p>
          </div>
        ) : (
          filteredAlerts.map((alt) => (
            <div
              key={alt.id}
              className={`glass-panel p-5 border-l-4 transition-all ${
                alt.severity === 'CRITICAL' ? 'border-l-rose-500 bg-rose-950/10' :
                alt.severity === 'WARNING' ? 'border-l-amber-500 bg-amber-950/10' :
                'border-l-blue-500'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded ${
                      alt.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                      alt.severity === 'WARNING' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                      'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                    }`}>
                      {alt.severity}
                    </span>
                    <span className="text-xs font-mono text-slate-400">ID: {alt.id}</span>
                  </div>
                  <h3 className="text-base font-bold text-white mt-1">{alt.title}</h3>
                  <p className="text-xs text-slate-300">{alt.description}</p>
                  
                  <div className="flex items-center gap-4 pt-2 text-[11px] text-slate-400">
                    {alt.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-slate-500" />
                        <span>Zone: {alt.location}</span>
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      <span>{alt.timestamp}</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
