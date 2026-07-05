import React from 'react';
import { useWorldStore } from '../state/useWorldStore';
import { useAuthStore } from '../state/useAuthStore';
import {
  Users,
  Clock,
  CheckCircle2,
  Sparkles,
  ArrowUpRight,
  Flame,
  ShieldAlert,
  Activity,
  ChevronRight,
  Utensils,
  MapPin,
  TrendingUp,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const LiveDashboard: React.FC = () => {
  const { kpis, recommendations, alerts, acknowledgeRecommendation } = useWorldStore();
  const { hasPermission } = useAuthStore();
  const navigate = useNavigate();

  const canOperatorAct = hasPermission(['Operator', 'Administrator']);
  const activeRecommendations = recommendations.filter((r) => !r.acknowledged);
  const occupancyRate = Math.round((kpis.currentOccupancy / kpis.maxCapacity) * 100);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>Live Operations Command Center</span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-normal">
              Real-time
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Continuous AI surveillance and operations research telemetry across restaurant zones.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/floor-plan')}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-sm transition-all flex items-center gap-2"
          >
            <Utensils className="w-4 h-4 text-emerald-400" />
            <span>View Floor Plan</span>
          </button>
          <button
            onClick={() => navigate('/digital-twin')}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-medium text-sm shadow-lg shadow-emerald-900/30 transition-all flex items-center gap-2"
          >
            <Activity className="w-4 h-4" />
            <span>Digital Twin Inspector</span>
          </button>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Occupancy Card */}
        <div className="glass-card bg-gradient-to-br from-slate-900/90 to-slate-900/40 border-slate-800 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Users className="w-20 h-20 text-emerald-400" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Current Occupancy</span>
            <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
              occupancyRate > 85 ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
            }`}>
              {occupancyRate}% Full
            </span>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{kpis.currentOccupancy}</span>
            <span className="text-sm text-slate-400">/ {kpis.maxCapacity} guests</span>
          </div>
          <div className="mt-3 w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${occupancyRate > 85 ? 'bg-rose-500' : 'bg-emerald-500'}`}
              style={{ width: `${Math.min(100, occupancyRate)}%` }}
            />
          </div>
          <p className="text-[11px] text-slate-400 mt-2 flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
            <span>+12% vs last Friday peak</span>
          </p>
        </div>

        {/* Queue Length Card */}
        <div className="glass-card bg-gradient-to-br from-slate-900/90 to-slate-900/40 border-slate-800 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Clock className="w-20 h-20 text-amber-400" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Host Stand Queue</span>
            <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
              kpis.queueLength > 6 ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
            }`}>
              {kpis.queueLength > 6 ? 'High Demand' : 'Normal Flow'}
            </span>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{kpis.queueLength}</span>
            <span className="text-sm text-slate-400">parties waiting</span>
          </div>
          <p className="text-xs text-amber-400 mt-3 font-medium flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            <span>~{kpis.expectedWaitMinutes} min expected wait</span>
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Estimated turn rate: 3 tables/10m</p>
        </div>

        {/* Table Status Card */}
        <div className="glass-card bg-gradient-to-br from-slate-900/90 to-slate-900/40 border-slate-800 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <CheckCircle2 className="w-20 h-20 text-teal-400" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Seating Status</span>
            <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-teal-500/20 text-teal-300 border border-teal-500/30">
              Live State
            </span>
          </div>
          <div className="mt-4 flex items-baseline gap-4">
            <div>
              <span className="text-3xl font-extrabold text-emerald-400">{kpis.availableTables}</span>
              <span className="text-xs text-slate-400 block">Available</span>
            </div>
            <div className="h-8 w-px bg-slate-800" />
            <div>
              <span className="text-3xl font-extrabold text-white">{kpis.activeTables}</span>
              <span className="text-xs text-slate-400 block">Occupied</span>
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mt-3">Total tracked sections: 8 tables</p>
        </div>

        {/* Kitchen & Staff Load Card */}
        <div className="glass-card bg-gradient-to-br from-slate-900/90 to-slate-900/40 border-slate-800 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Flame className="w-20 h-20 text-rose-400" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Back-of-House Load</span>
            <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
              kpis.kitchenLoadPercent > 80 ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
            }`}>
              {kpis.kitchenLoadPercent}% Capacity
            </span>
          </div>
          <div className="mt-4">
            <div className="flex justify-between text-xs text-slate-300 mb-1">
              <span>Kitchen Ticket Pressure</span>
              <span className="font-bold">{kpis.kitchenLoadPercent}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div className="bg-rose-500 h-full" style={{ width: `${kpis.kitchenLoadPercent}%` }} />
            </div>
            <div className="flex justify-between text-xs text-slate-300 mt-3 mb-1">
              <span>Staff Availability</span>
              <span className="font-bold text-emerald-400">{kpis.staffAvailabilityPercent}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div className="bg-emerald-500 h-full" style={{ width: `${kpis.staffAvailabilityPercent}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Recommendations & Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recommendation Center (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">AI Decision & Optimization Recommendations</h2>
                <p className="text-xs text-slate-400">Ranked operational interventions generated by classical operations research engines.</p>
              </div>
            </div>
            <button
              onClick={() => navigate('/recommendations')}
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
            >
              <span>View All ({recommendations.length})</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-3">
            {activeRecommendations.length === 0 ? (
              <div className="glass-card text-center py-8">
                <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
                <p className="text-sm font-semibold text-white">All clear! No pending operational interventions.</p>
                <p className="text-xs text-slate-400 mt-1">The restaurant is operating at optimal throughput efficiency.</p>
              </div>
            ) : (
              activeRecommendations.map((rec) => (
                <div key={rec.id} className="glass-card border-l-4 border-l-emerald-500 hover:bg-slate-900/80 transition-all">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded ${
                          rec.priority === 'HIGH' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        }`}>
                          {rec.priority} PRIORITY
                        </span>
                        <span className="text-xs text-slate-400 font-mono">ID: {rec.id}</span>
                        <span className="text-xs text-emerald-400 font-semibold">• Confidence: {Math.round(rec.confidence * 100)}%</span>
                      </div>
                      <h3 className="text-base font-bold text-white">{rec.title}</h3>
                      <p className="text-xs text-slate-300 leading-relaxed">{rec.reason}</p>
                      
                      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 space-y-1 mt-2">
                        <p className="text-[11px] text-emerald-400 font-semibold flex items-center gap-1.5">
                          <ArrowUpRight className="w-3.5 h-3.5" />
                          <span>Expected Benefit: {rec.expectedBenefit}</span>
                        </p>
                        <p className="text-[11px] text-slate-400">
                          <strong className="text-slate-300">Evidence:</strong> {rec.evidence.join(' • ')}
                        </p>
                      </div>
                    </div>

                    <div className="flex sm:flex-col items-center justify-end gap-2 flex-shrink-0">
                      {canOperatorAct ? (
                        <button
                          onClick={() => acknowledgeRecommendation(rec.id)}
                          className="w-full sm:w-auto px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs shadow-lg shadow-emerald-900/30 transition-all flex items-center justify-center gap-1.5"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Execute Action</span>
                        </button>
                      ) : (
                        <span className="text-[10px] text-slate-500 italic">Read-only permissions</span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Live Alerts & System Telemetry (1 col) */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Live Alert Center</h2>
                <p className="text-xs text-slate-400">Real-time anomaly stream.</p>
              </div>
            </div>
            <button
              onClick={() => navigate('/alerts')}
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
            >
              <span>History</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-3">
            {alerts.slice(0, 4).map((alert) => (
              <div key={alert.id} className="glass-card p-4 hover:border-slate-700 transition-all">
                <div className="flex items-center justify-between mb-2">
                  <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded ${
                    alert.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                    alert.severity === 'WARNING' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                    'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                  }`}>
                    {alert.severity}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">{alert.timestamp}</span>
                </div>
                <h4 className="text-sm font-bold text-white">{alert.title}</h4>
                <p className="text-xs text-slate-300 mt-1">{alert.description}</p>
                {alert.location && (
                  <p className="text-[11px] text-slate-400 mt-2 flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-slate-500" />
                    <span>Zone: {alert.location}</span>
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
