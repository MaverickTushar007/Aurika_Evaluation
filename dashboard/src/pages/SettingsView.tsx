import React, { useState } from 'react';
import { useAuthStore } from '../state/useAuthStore';
import {
  Settings,
  ShieldAlert,
  Sliders,
  Database,
  Bell,
  CheckCircle2,
  Lock,
  Server,
} from 'lucide-react';

export const SettingsView: React.FC = () => {
  const { user, hasPermission } = useAuthStore();
  const isAdmin = hasPermission(['Administrator']);

  const [queueThreshold, setQueueThreshold] = useState(6);
  const [cleanTimeout, setCleanTimeout] = useState(8);
  const [fpsAlertThreshold, setFpsAlertThreshold] = useState(20);
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>Platform Configuration & Threshold Settings</span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-normal">
              Enterprise Admin
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Configure surveillance sensitivity, operational alert rules, and WebSocket telemetry frequencies.
          </p>
        </div>
      </div>

      {!isAdmin ? (
        <div className="glass-panel p-8 text-center border-rose-500/30">
          <Lock className="w-12 h-12 text-rose-400 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-white">Administrator Access Required</h2>
          <p className="text-sm text-slate-400 mt-1">
            You are currently logged in as <strong className="text-slate-200">{user?.role}</strong>. Platform settings mutation is restricted to Administrator roles.
          </p>
        </div>
      ) : (
        <form onSubmit={handleSave} className="space-y-6">
          {saved && (
            <div className="p-4 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 flex items-center gap-3 animate-fadeIn">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
              <span className="text-sm font-semibold">Configuration updated successfully across Aurika Platform Storage repository.</span>
            </div>
          )}

          {/* Operational Thresholds Panel */}
          <div className="glass-panel p-6 space-y-6">
            <div className="flex items-center gap-2 pb-4 border-b border-slate-800">
              <Sliders className="w-5 h-5 text-emerald-400" />
              <h2 className="text-base font-bold text-white">Decision & Optimization Threshold Rules</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-2">
                  Host Queue Bottleneck Trigger (Parties)
                </label>
                <input
                  type="number"
                  value={queueThreshold}
                  onChange={(e) => setQueueThreshold(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-white font-mono focus:outline-none focus:border-emerald-500"
                />
                <span className="text-[11px] text-slate-500 block mt-1">Raises WARNING alert when queue length exceeds this value.</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-2">
                  Table Bussing Latency Limit (Minutes)
                </label>
                <input
                  type="number"
                  value={cleanTimeout}
                  onChange={(e) => setCleanTimeout(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-white font-mono focus:outline-none focus:border-emerald-500"
                />
                <span className="text-[11px] text-slate-500 block mt-1">Triggers HIGH priority busser dispatch recommendation.</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-2">
                  Min Inference FPS Threshold
                </label>
                <input
                  type="number"
                  value={fpsAlertThreshold}
                  onChange={(e) => setFpsAlertThreshold(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-white font-mono focus:outline-none focus:border-emerald-500"
                />
                <span className="text-[11px] text-slate-500 block mt-1">Alerts system engineer if TensorRT edge FPS drops below limit.</span>
              </div>
            </div>
          </div>

          {/* Network & Service Endpoints */}
          <div className="glass-panel p-6 space-y-4">
            <div className="flex items-center gap-2 pb-4 border-b border-slate-800">
              <Server className="w-5 h-5 text-blue-400" />
              <h2 className="text-base font-bold text-white">Platform Gateway & WebSocket Telemetry Endpoints</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <span className="text-xs text-slate-400 block mb-1">REST API Gateway Host:</span>
                <input
                  type="text"
                  disabled
                  value="http://localhost:8000/api/v1"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-slate-400 font-mono opacity-80 cursor-not-allowed"
                />
              </div>
              <div>
                <span className="text-xs text-slate-400 block mb-1">WebSocket Telemetry Stream:</span>
                <input
                  type="text"
                  disabled
                  value="ws://localhost:8000/ws"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-slate-400 font-mono opacity-80 cursor-not-allowed"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              className="px-8 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-900/30 transition-all"
            >
              Save Configuration Rules
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
