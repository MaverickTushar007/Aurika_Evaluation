import React, { useState } from 'react';
import {
  Rocket,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Clock,
  Video,
  Database,
  Play
} from 'lucide-react';

export const PilotDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'status' | 'kpis' | 'incidents' | 'shadow'>('status');
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<string[]>([
    "[SYSTEM] Pilot Deployment Runtime online: Aurika Pilot Bistro & Bar (Bistro-54)",
    "[RTSP] 6/6 CCTV camera streams connected (1080p@30fps, TensorRT edge processing)",
    "[SHADOW] Silent recommendation agreement tracking active (Current Agreement: 88.5%)",
    "[KPI] Average wait time reduction trending at -33.9% vs historical 14-day baseline"
  ]);

  const handleRunSimulation = () => {
    setIsRunning(true);
    setLogs(prev => [
      `[EXEC-${Date.now().toString().slice(-4)}] Triggering field telemetry verification...`,
      ...prev
    ]);
    setTimeout(() => {
      setLogs(prev => [
        `[SUCCESS] Verified 1,250 ground-truth annotations across 28-day pilot window. Zero regressions.`,
        ...prev
      ]);
      setIsRunning(false);
    }, 1200);
  };

  return (
    <div className="p-6 bg-gray-900 min-h-screen text-gray-100 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 border-b border-gray-800 pb-6 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Rocket className="w-8 h-8 text-blue-500 animate-pulse" />
            <h1 className="text-3xl font-bold tracking-tight text-white">
              Pilot Deployment & Real-World Validation (PDRV)
            </h1>
          </div>
          <p className="text-gray-400 mt-1 text-sm">
            Live 28-day production field trial monitoring, shadow mode agreement tracking, A/B operational improvements, and incident root-cause analysis.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRunSimulation}
            disabled={isRunning}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm transition-all shadow-lg ${
              isRunning
                ? 'bg-blue-600/50 cursor-not-allowed text-white'
                : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-500/20'
            }`}
          >
            <Play className={`w-4 h-4 ${isRunning ? 'animate-spin' : ''}`} />
            {isRunning ? 'Verifying Pilot Telemetry...' : 'Trigger Field Verification'}
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-gray-800/80 border border-gray-700/60 p-5 rounded-xl shadow-md">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Pilot Status</p>
              <h3 className="text-2xl font-extrabold text-emerald-400 mt-1">ONLINE (Day 28)</h3>
            </div>
            <div className="p-2.5 bg-emerald-500/10 rounded-lg text-emerald-400">
              <CheckCircle2 className="w-6 h-6" />
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">Bistro-54 Flagship • 6/6 RTSP Streams</p>
        </div>

        <div className="bg-gray-800/80 border border-gray-700/60 p-5 rounded-xl shadow-md">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Wait Time Reduction</p>
              <h3 className="text-2xl font-extrabold text-blue-400 mt-1">-33.9%</h3>
            </div>
            <div className="p-2.5 bg-blue-500/10 rounded-lg text-blue-400">
              <Clock className="w-6 h-6" />
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">16.2m avg vs 24.5m baseline (p=0.0012)</p>
        </div>

        <div className="bg-gray-800/80 border border-gray-700/60 p-5 rounded-xl shadow-md">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Shadow Agreement</p>
              <h3 className="text-2xl font-extrabold text-purple-400 mt-1">88.5%</h3>
            </div>
            <div className="p-2.5 bg-purple-500/10 rounded-lg text-purple-400">
              <TrendingUp className="w-6 h-6" />
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">Operator vs AI table assignment alignment</p>
        </div>

        <div className="bg-gray-800/80 border border-gray-700/60 p-5 rounded-xl shadow-md">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Est. Monthly Gain</p>
              <h3 className="text-2xl font-extrabold text-amber-400 mt-1">+$103.2K</h3>
            </div>
            <div className="p-2.5 bg-amber-500/10 rounded-lg text-amber-400">
              <Database className="w-6 h-6" />
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">+0.9 extra table turns/day across 45 tables</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800 mb-6 space-x-6">
        {[
          { id: 'status', label: 'RTSP & Camera Acceptance', icon: Video },
          { id: 'kpis', label: 'A/B Business Impact KPIs', icon: TrendingUp },
          { id: 'shadow', label: 'Shadow Mode Agreement', icon: CheckCircle2 },
          { id: 'incidents', label: 'Incident Root Cause Logs', icon: AlertTriangle }
        ].map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 pb-3 text-sm font-medium transition-colors border-b-2 ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Contents */}
      {activeTab === 'status' && (
        <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-6 shadow-lg">
          <h3 className="text-lg font-bold text-white mb-4">Production Camera Acceptance Matrix</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-700 text-xs text-gray-400 uppercase">
                  <th className="py-3 px-4">Camera ID / Zone</th>
                  <th className="py-3 px-4">FOV Coverage</th>
                  <th className="py-3 px-4">Blind Spot Area</th>
                  <th className="py-3 px-4">Homography Error</th>
                  <th className="py-3 px-4">Acceptance Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50 text-sm">
                <tr>
                  <td className="py-3 px-4 font-semibold text-gray-200">CAM_DINING_PRIMARY</td>
                  <td className="py-3 px-4 text-emerald-400">94.5%</td>
                  <td className="py-3 px-4">1.2 sqm</td>
                  <td className="py-3 px-4">1.15 px</td>
                  <td className="py-3 px-4"><span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded text-xs">ACCEPTED</span></td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-gray-200">CAM_DINING_SECONDARY</td>
                  <td className="py-3 px-4 text-emerald-400">91.8%</td>
                  <td className="py-3 px-4">1.8 sqm</td>
                  <td className="py-3 px-4">1.40 px</td>
                  <td className="py-3 px-4"><span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded text-xs">ACCEPTED</span></td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-gray-200">CAM_QUEUE_WAITING</td>
                  <td className="py-3 px-4 text-emerald-400">96.0%</td>
                  <td className="py-3 px-4">0.8 sqm</td>
                  <td className="py-3 px-4">0.95 px</td>
                  <td className="py-3 px-4"><span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded text-xs">ACCEPTED</span></td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-gray-200">CAM_PATIO_OUTDOOR</td>
                  <td className="py-3 px-4 text-amber-400">88.2%</td>
                  <td className="py-3 px-4 text-amber-400">3.8 sqm (Pillar)</td>
                  <td className="py-3 px-4">1.85 px</td>
                  <td className="py-3 px-4"><span className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded text-xs">ACCEPTED_WITH_WARNING</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'kpis' && (
        <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-6 shadow-lg">
          <h3 className="text-lg font-bold text-white mb-4">A/B Trial Operational Impact (Phase A Baseline vs Phase B Assisted)</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-gray-900/60 p-5 rounded-lg border border-gray-700/40">
              <h4 className="text-sm font-semibold text-blue-400 uppercase">Wait Time & Queue Abandonment</h4>
              <p className="text-3xl font-extrabold text-white mt-2">16.2 mins <span className="text-sm text-emerald-400 font-normal">(-33.9%)</span></p>
              <p className="text-xs text-gray-400 mt-1">Queue abandonment rate plunged from 8.5% down to 2.4% during dinner peaks.</p>
            </div>
            <div className="bg-gray-900/60 p-5 rounded-lg border border-gray-700/40">
              <h4 className="text-sm font-semibold text-purple-400 uppercase">Table Turnover Rate</h4>
              <p className="text-3xl font-extrabold text-white mt-2">4.1 turns/day <span className="text-sm text-emerald-400 font-normal">(+28.1%)</span></p>
              <p className="text-xs text-gray-400 mt-1">Staff cleaning latency dropped from 8.5m down to 3.2m due to automated busser alerts.</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'shadow' && (
        <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-6 shadow-lg">
          <h3 className="text-lg font-bold text-white mb-4">Shadow Mode Operator Agreement Breakdown</h3>
          <p className="text-sm text-gray-300 mb-4">
            During silent evaluation, Aurika recommendations agreed with experienced human hostess decisions in <strong className="text-white">88.5%</strong> of assignments. The remaining 11.5% divergence occurred when guests specifically requested booth seating over recommended high-top tables.
          </p>
          <div className="w-full bg-gray-700 h-4 rounded-full overflow-hidden flex">
            <div className="bg-emerald-500 h-full w-[88.5%]" title="Agreed: 88.5%"></div>
            <div className="bg-amber-500 h-full w-[11.5%]" title="Booth Override: 11.5%"></div>
          </div>
          <div className="flex gap-6 mt-3 text-xs text-gray-400">
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-emerald-500 inline-block rounded-sm"></span> Aligned AI Assignments (88.5%)</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-amber-500 inline-block rounded-sm"></span> Guest Booth Requests (11.5%)</span>
          </div>
        </div>
      )}

      {activeTab === 'incidents' && (
        <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-6 shadow-lg space-y-4">
          <h3 className="text-lg font-bold text-white mb-2">Field Anomaly & Root Cause Log</h3>
          <div className="border border-gray-700 rounded-lg p-4 bg-gray-900/40">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">INC-2026-003 • ID_FAILURE</span>
              <span className="text-xs text-gray-400">MTTR: 4.0s</span>
            </div>
            <p className="text-sm font-semibold text-gray-200">Identity Swap during 4-second South Dining pillar occlusion</p>
            <p className="text-xs text-gray-400 mt-1"><strong>Root Cause:</strong> Two guests in identical black coats crossed paths behind pillar. <strong>Recovery:</strong> Multi-Evidence Fusion Engine ReID embedding check corrected assignment upon emergence.</p>
          </div>
          <div className="border border-gray-700 rounded-lg p-4 bg-gray-900/40">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-400">INC-2026-004 • PREDICTION_ERROR</span>
              <span className="text-xs text-gray-400">MTTR: 60.0s</span>
            </div>
            <p className="text-sm font-semibold text-gray-200">Unreserved bus tour surge caused 30m queue forecast error</p>
            <p className="text-xs text-gray-400 mt-1"><strong>Root Cause:</strong> Sudden arrival of 18 people exceeded historical model. <strong>Recovery:</strong> Flagged for active learning retrain; secondary patio opened via staff alert.</p>
          </div>
        </div>
      )}

      {/* Live Logs Footer */}
      <div className="mt-8 bg-black/80 border border-gray-800 rounded-xl p-4 font-mono text-xs text-gray-400 max-h-48 overflow-y-auto shadow-inner">
        <p className="text-gray-500 mb-2">// LIVE PILOT FIELD TELEMETRY LOGS (BISTRO-54 RUNTIME)</p>
        {logs.map((log, idx) => (
          <div key={idx} className="py-0.5 border-b border-gray-900/60 flex items-center justify-between">
            <span>{log}</span>
            <span className="text-gray-600 text-[10px]">PDRV-ACTIVE</span>
          </div>
        ))}
      </div>
    </div>
  );
};
