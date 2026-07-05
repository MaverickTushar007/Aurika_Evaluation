import React, { useState } from 'react';
import { 
  TrendingUp, Clock, Users, AlertTriangle, Play, RefreshCw, 
  FileText, ArrowRight, CheckCircle2, ShieldAlert, Sliders,
  Calendar, Layers, Sparkles, Activity
} from 'lucide-react';

interface ForecastData {
  horizon: number;
  occupancy: number;
  utilization: number;
  queueLen: number;
  avgWait: number;
  waiterLoad: number;
  kitchenLoad: number;
  action: string;
}

const BASE_FORECASTS: Record<number, ForecastData> = {
  5: { horizon: 5, occupancy: 78, utilization: 65.0, queueLen: 8.5, avgWait: 12.0, waiterLoad: 68.0, kitchenLoad: 64.0, action: 'STANDARD_HOST_SEATING' },
  10: { horizon: 10, occupancy: 94, utilization: 78.3, queueLen: 14.2, avgWait: 18.5, waiterLoad: 82.0, kitchenLoad: 76.0, action: 'STANDARD_HOST_SEATING' },
  30: { horizon: 30, occupancy: 145, utilization: 92.5, queueLen: 26.8, avgWait: 34.0, waiterLoad: 94.0, kitchenLoad: 88.0, action: 'ACTIVATE_VIRTUAL_SMS_QUEUE' },
  60: { horizon: 60, occupancy: 168, utilization: 96.0, queueLen: 31.5, avgWait: 42.5, waiterLoad: 98.0, kitchenLoad: 92.0, action: 'OPEN_OVERFLOW_PATIO_SECTION' }
};

export const ForecastDashboard: React.FC = () => {
  const [selectedHorizon, setSelectedHorizon] = useState<number>(30);
  const [scenarioType, setScenarioType] = useState<string>('SURGE_30_GUESTS');
  const [customArrivalDelta, setCustomArrivalDelta] = useState<number>(30);
  const [customWaiterDelta, setCustomWaiterDelta] = useState<number>(0);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'timeline' | 'simulator' | 'capacity'>('timeline');

  // Compute simulated data based on user perturbation sliders
  const currentData = BASE_FORECASTS[selectedHorizon];
  const simArrivalFactor = (customArrivalDelta / 30.0);
  const simWaiterFactor = customWaiterDelta === 0 ? 1.0 : (6.0 / Math.max(1, 6 + customWaiterDelta));
  
  const simOccupancy = Math.min(200, Math.round(currentData.occupancy + (customArrivalDelta * (selectedHorizon / 60))));
  const simQueue = Math.max(0, Math.round(currentData.queueLen + (customArrivalDelta * 0.4) * simWaiterFactor));
  const simWait = Math.max(1, Math.round(currentData.avgWait + (customArrivalDelta * 0.6) * simWaiterFactor));
  const simWaiterLoad = Math.min(100, Math.round(currentData.waiterLoad * simWaiterFactor + (customArrivalDelta * 0.3)));
  const simUtil = Math.min(100, Math.round((simOccupancy / 180) * 100));

  const isBottleneck = simQueue > 20 || simWait > 25 || simUtil > 90;

  const handleRunSimulation = () => {
    setIsSimulating(true);
    setTimeout(() => {
      setIsSimulating(false);
    }, 600);
  };

  const handleExport = (format: string) => {
    alert(`Exporting Phase 15 Operational Forecast Report as [${format.toUpperCase()}]... Check downloads / backend logs!`);
  };

  return (
    <div className="space-y-6 animate-fade-in p-6 bg-slate-950 min-h-screen text-slate-100 font-sans">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-indigo-900/60 via-purple-900/40 to-slate-900/80 p-6 rounded-2xl border border-indigo-500/30 backdrop-blur-md shadow-2xl">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-500/20 rounded-xl border border-indigo-400/30">
              <Sparkles className="w-6 h-6 text-indigo-400 animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-white via-indigo-200 to-purple-300 bg-clip-text text-transparent">
                Predictive Intelligence & Forecasting Engine
              </h1>
              <p className="text-sm text-slate-400">
                Project Aurika Phase 15 • Multi-Horizon Projections • What-If Scenario Simulator
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => handleExport('JSON')}
            className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-300 transition-all flex items-center gap-1.5"
          >
            <FileText className="w-3.5 h-3.5 text-indigo-400" /> Export JSON
          </button>
          <button 
            onClick={() => handleExport('CSV')}
            className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-300 transition-all flex items-center gap-1.5"
          >
            <FileText className="w-3.5 h-3.5 text-purple-400" /> Export CSV
          </button>
          <button 
            onClick={() => handleExport('PDF')}
            className="px-4 py-2 text-xs font-bold rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-1.5"
          >
            <FileText className="w-3.5 h-3.5" /> Generate PDF Report
          </button>
        </div>
      </div>

      {/* Horizon Selector & Navigation Tabs */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-2">Forecast Horizon:</span>
          {[5, 10, 30, 60].map((h) => (
            <button
              key={h}
              onClick={() => setSelectedHorizon(h)}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${
                selectedHorizon === h
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/40 border border-indigo-400/50 scale-105'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
              }`}
            >
              +{h}m
            </button>
          ))}
        </div>

        <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800">
          {(['timeline', 'simulator', 'capacity'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all ${
                activeTab === tab
                  ? 'bg-slate-800 text-indigo-400 shadow-sm border border-slate-700'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {tab === 'timeline' ? 'Timeline Projection' : tab === 'simulator' ? 'What-If Simulator' : 'Capacity & Recommendations'}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Areas based on Tab */}
      {activeTab === 'timeline' && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Key Metrics Cards */}
          <div className="bg-gradient-to-br from-slate-900/90 to-slate-900/50 p-5 rounded-2xl border border-slate-800 shadow-xl relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-semibold uppercase">Predicted Occupancy</span>
              <Users className="w-5 h-5 text-indigo-400" />
            </div>
            <div className="text-3xl font-black text-white">{currentData.occupancy} <span className="text-sm font-normal text-slate-400">/ 200</span></div>
            <div className="mt-3 flex items-center justify-between text-xs font-medium">
              <span className="text-slate-400">Table Util: {currentData.utilization}%</span>
              <span className="text-indigo-400 font-bold">+{selectedHorizon}m Horizon</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
              <div className="bg-gradient-to-r from-indigo-500 to-purple-500 h-full rounded-full transition-all duration-500" style={{ width: `${currentData.utilization}%` }} />
            </div>
          </div>

          <div className="bg-gradient-to-br from-slate-900/90 to-slate-900/50 p-5 rounded-2xl border border-slate-800 shadow-xl relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-semibold uppercase">Host Queue Length</span>
              <Clock className="w-5 h-5 text-amber-400" />
            </div>
            <div className="text-3xl font-black text-amber-300">{currentData.queueLen} <span className="text-sm font-normal text-slate-400">parties</span></div>
            <div className="mt-3 flex items-center justify-between text-xs font-medium">
              <span className="text-slate-400">Avg Wait: {currentData.avgWait}m</span>
              <span className={currentData.avgWait > 25 ? "text-rose-400 font-bold" : "text-emerald-400 font-bold"}>
                {currentData.avgWait > 25 ? "Bottleneck Risk" : "Stable Flow"}
              </span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
              <div className="bg-gradient-to-r from-amber-500 to-rose-500 h-full rounded-full transition-all duration-500" style={{ width: `${Math.min(100, (currentData.queueLen / 35) * 100)}%` }} />
            </div>
          </div>

          <div className="bg-gradient-to-br from-slate-900/90 to-slate-900/50 p-5 rounded-2xl border border-slate-800 shadow-xl relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-semibold uppercase">Waiter Workload Index</span>
              <Activity className="w-5 h-5 text-purple-400" />
            </div>
            <div className="text-3xl font-black text-purple-300">{currentData.waiterLoad}%</div>
            <div className="mt-3 flex items-center justify-between text-xs font-medium">
              <span className="text-slate-400">Active Waiters: 6</span>
              <span className={currentData.waiterLoad > 90 ? "text-rose-400 font-bold" : "text-purple-400 font-bold"}>
                {currentData.waiterLoad > 90 ? "High Stress" : "Balanced"}
              </span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
              <div className="bg-gradient-to-r from-purple-500 to-rose-500 h-full rounded-full transition-all duration-500" style={{ width: `${currentData.waiterLoad}%` }} />
            </div>
          </div>

          <div className="bg-gradient-to-br from-slate-900/90 to-slate-900/50 p-5 rounded-2xl border border-slate-800 shadow-xl relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-semibold uppercase">Overflow Action</span>
              <ShieldAlert className="w-5 h-5 text-rose-400" />
            </div>
            <div className="text-sm font-extrabold text-white mt-1 leading-snug">{currentData.action.replace(/_/g, ' ')}</div>
            <div className="mt-4 flex items-center gap-1.5 text-xs font-semibold text-indigo-400">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Proactive DOE Override Active
            </div>
          </div>

          {/* Timeline Projections Table */}
          <div className="md:col-span-4 bg-slate-900/60 rounded-2xl border border-slate-800 p-6 shadow-xl">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-indigo-400" /> Multi-Horizon Operational Forecast Breakdown
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 text-xs uppercase font-semibold">
                    <th className="py-3 px-4">Horizon</th>
                    <th className="py-3 px-4">Predicted Occupancy</th>
                    <th className="py-3 px-4">Table Util (%)</th>
                    <th className="py-3 px-4">Queue Length</th>
                    <th className="py-3 px-4">Avg Wait (min)</th>
                    <th className="py-3 px-4">Waiter Load</th>
                    <th className="py-3 px-4">Recommended Action</th>
                    <th className="py-3 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-medium">
                  {Object.values(BASE_FORECASTS).map((row) => (
                    <tr key={row.horizon} className={`hover:bg-slate-800/40 transition-colors ${row.horizon === selectedHorizon ? 'bg-indigo-950/30 border-l-4 border-indigo-500' : ''}`}>
                      <td className="py-3.5 px-4 font-bold text-indigo-300">+{row.horizon}m</td>
                      <td className="py-3.5 px-4 text-white">{row.occupancy} guests</td>
                      <td className="py-3.5 px-4 text-slate-300">{row.utilization}%</td>
                      <td className="py-3.5 px-4 text-amber-300 font-semibold">{row.queueLen}</td>
                      <td className="py-3.5 px-4 text-slate-200">{row.avgWait}m</td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${row.waiterLoad > 90 ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'bg-purple-500/20 text-purple-300'}`}>
                          {row.waiterLoad}%
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-xs font-semibold text-slate-300">{row.action.replace(/_/g, ' ')}</td>
                      <td className="py-3.5 px-4">
                        {row.avgWait > 30 ? (
                          <span className="flex items-center gap-1 text-xs font-bold text-rose-400">
                            <AlertTriangle className="w-3.5 h-3.5" /> Bottleneck
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-xs font-bold text-emerald-400">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Normal
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Scenario Simulator Tab */}
      {activeTab === 'simulator' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-fade-in">
          {/* Controls Column */}
          <div className="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-6">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Sliders className="w-5 h-5 text-indigo-400" /> Scenario Parameters
            </h2>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Preset Perturbation:</label>
              <select
                value={scenarioType}
                onChange={(e) => {
                  setScenarioType(e.target.value);
                  if (e.target.value === 'SURGE_30_GUESTS') { setCustomArrivalDelta(30); setCustomWaiterDelta(0); }
                  else if (e.target.value === 'WAITER_LEAVES') { setCustomArrivalDelta(0); setCustomWaiterDelta(-1); }
                  else if (e.target.value === 'CAMERA_FAILS') { setCustomArrivalDelta(10); setCustomWaiterDelta(0); }
                  else { setCustomArrivalDelta(45); setCustomWaiterDelta(-2); }
                }}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-sm font-semibold text-white focus:outline-none focus:border-indigo-500 transition-all"
              >
                <option value="SURGE_30_GUESTS">⚡ Surge: +30 Guests/Hour Arrival Rate</option>
                <option value="WAITER_LEAVES">👤 Staff Loss: -1 Active Waiter Shift</option>
                <option value="CAMERA_FAILS">📹 Sensor Failure: 1 Primary Camera Offline</option>
                <option value="EXTREME_OVERFLOW">🚨 Extreme Holiday Rush (+45 Guests, -2 Staff)</option>
              </select>
            </div>

            <div className="space-y-4 pt-2 border-t border-slate-800">
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-300 mb-1">
                  <span>Arrival Surge Delta (guests/hr):</span>
                  <span className="text-indigo-400">+{customArrivalDelta}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="60"
                  step="5"
                  value={customArrivalDelta}
                  onChange={(e) => setCustomArrivalDelta(Number(e.target.value))}
                  className="w-full accent-indigo-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-300 mb-1">
                  <span>Waiter Staff Adjustment:</span>
                  <span className={customWaiterDelta < 0 ? "text-rose-400" : "text-emerald-400"}>{customWaiterDelta >= 0 ? `+${customWaiterDelta}` : customWaiterDelta} waiters</span>
                </div>
                <input
                  type="range"
                  min="-3"
                  max="3"
                  step="1"
                  value={customWaiterDelta}
                  onChange={(e) => setCustomWaiterDelta(Number(e.target.value))}
                  className="w-full accent-indigo-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
                />
              </div>
            </div>

            <button
              onClick={handleRunSimulation}
              disabled={isSimulating}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              {isSimulating ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5 fill-current" />}
              {isSimulating ? "Running Monte Carlo Sim..." : "Execute What-If Simulation"}
            </button>
          </div>

          {/* Simulated Results Column */}
          <div className="md:col-span-2 bg-slate-900/60 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-extrabold text-white">Simulated Telemetry (+{selectedHorizon}m Horizon)</h3>
                <p className="text-xs text-slate-400">Comparing baseline vs perturbed scenario projection</p>
              </div>
              {isBottleneck ? (
                <span className="px-3 py-1 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-300 text-xs font-bold flex items-center gap-1.5 animate-pulse">
                  <AlertTriangle className="w-4 h-4" /> Critical Bottleneck Risk
                </span>
              ) : (
                <span className="px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-bold flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> Manageable Capacity Flow
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block mb-1">Simulated Occupancy</span>
                <div className="text-2xl font-black text-white">{simOccupancy}</div>
                <span className="text-xs font-semibold text-indigo-400">vs {currentData.occupancy} baseline</span>
              </div>
              <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block mb-1">Simulated Queue</span>
                <div className="text-2xl font-black text-amber-300">{simQueue}</div>
                <span className="text-xs font-semibold text-amber-400">+{Math.max(0, simQueue - currentData.queueLen)} parties</span>
              </div>
              <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block mb-1">Simulated Wait Time</span>
                <div className="text-2xl font-black text-rose-300">{simWait}m</div>
                <span className="text-xs font-semibold text-rose-400">vs {currentData.avgWait}m baseline</span>
              </div>
              <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block mb-1">Waiter Workload</span>
                <div className="text-2xl font-black text-purple-300">{simWaiterLoad}%</div>
                <span className="text-xs font-semibold text-purple-400">Index Score</span>
              </div>
            </div>

            <div className="bg-gradient-to-r from-slate-950 via-indigo-950/30 to-slate-950 p-5 rounded-xl border border-indigo-500/30 space-y-3">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" /> Prescriptive DOE & Capacity Recommendations
              </h4>
              <p className="text-xs text-slate-300 leading-relaxed">
                {isBottleneck 
                  ? `RECOMMENDATION: Immediately call in +${Math.max(1, Math.ceil(customArrivalDelta / 15))} standby waiters and switch Host Stand to SMS Virtual Waitlist. Proactive override triggered for Table 14 busing to clear ${simQueue} waiting parties before ${simWait}m wait threshold is breached.`
                  : "RECOMMENDATION: Standard host seating schedule remains optimal. Maintain current staff allocation and continue monitoring queue accumulation at +30m interval."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Capacity Planning & Recommendations Tab */}
      {activeTab === 'capacity' && (
        <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 shadow-xl space-y-6 animate-fade-in">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-purple-400" /> Resource Allocation & Staffing Plan (+{selectedHorizon}m Horizon)
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-slate-950/80 p-5 rounded-xl border border-slate-800 space-y-3">
              <h3 className="text-sm font-bold text-indigo-300 uppercase tracking-wider">Labor Requirements</h3>
              <ul className="text-xs space-y-2 text-slate-300 font-medium">
                <li className="flex justify-between border-b border-slate-800/60 pb-1.5"><span>Active Waiters:</span> <span className="font-bold text-white">8 staff (+2 recommended)</span></li>
                <li className="flex justify-between border-b border-slate-800/60 pb-1.5"><span>Table Bussers:</span> <span className="font-bold text-white">4 staff (+1 recommended)</span></li>
                <li className="flex justify-between"><span>Kitchen Cooks:</span> <span className="font-bold text-white">5 staff (optimal)</span></li>
              </ul>
            </div>

            <div className="bg-slate-950/80 p-5 rounded-xl border border-slate-800 space-y-3">
              <h3 className="text-sm font-bold text-purple-300 uppercase tracking-wider">Table Allocation Strategy</h3>
              <ul className="text-xs space-y-2 text-slate-300 font-medium">
                <li className="flex justify-between border-b border-slate-800/60 pb-1.5"><span>Couples / 2-Tops:</span> <span className="font-bold text-white">50% floor priority</span></li>
                <li className="flex justify-between border-b border-slate-800/60 pb-1.5"><span>Family / 4-Tops:</span> <span className="font-bold text-white">35% standard allocation</span></li>
                <li className="flex justify-between"><span>Large Banquets (5+):</span> <span className="font-bold text-white">15% reserved section</span></li>
              </ul>
            </div>

            <div className="bg-slate-950/80 p-5 rounded-xl border border-slate-800 space-y-3">
              <h3 className="text-sm font-bold text-amber-300 uppercase tracking-wider">Overflow & Queue Limit</h3>
              <ul className="text-xs space-y-2 text-slate-300 font-medium">
                <li className="flex justify-between border-b border-slate-800/60 pb-1.5"><span>Queue Capacity Cap:</span> <span className="font-bold text-white">30 parties max</span></li>
                <li className="flex justify-between border-b border-slate-800/60 pb-1.5"><span>Overflow Action:</span> <span className="font-bold text-amber-400">Activate SMS Virtual Queue</span></li>
                <li className="flex justify-between"><span>Section Status:</span> <span className="font-bold text-emerald-400">All Sections Open</span></li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default ForecastDashboard;
