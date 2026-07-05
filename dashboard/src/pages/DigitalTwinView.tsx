import React, { useState } from 'react';
import { useWorldStore } from '../state/useWorldStore';
import {
  Layers,
  Clock,
  Play,
  Pause,
  RotateCcw,
  Database,
  Activity,
  Calendar,
  CheckCircle2,
  FileCode,
} from 'lucide-react';

export const DigitalTwinView: React.FC = () => {
  const { kpis, tables } = useWorldStore();
  const [isPlaying, setIsPlaying] = useState(false);
  const [timeStep, setTimeStep] = useState(100); // 100% is current state

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>Restaurant Digital Twin (RDT) World State</span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30 font-normal">
              State Machine
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Continuously synchronized operational world representation consuming perception and fusion pipelines.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setTimeStep(100)}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl border border-slate-700 text-xs font-semibold flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5 text-emerald-400" />
            <span>Sync to Live</span>
          </button>
        </div>
      </div>

      {/* Timeline Scrubbing & Replay Bar */}
      <div className="glass-panel p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="w-10 h-10 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center shadow-lg shadow-emerald-900/30 transition-all"
            >
              {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 translate-x-0.5" />}
            </button>
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block">Timeline Replay Scrubber</span>
              <span className="text-sm font-bold text-white">
                {timeStep === 100 ? 'Live Synchronized State (Present)' : `Historical Simulation Snapshot (-${100 - timeStep} mins)`}
              </span>
            </div>
          </div>
          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/30">
            Step: {timeStep}/100
          </span>
        </div>

        <div className="space-y-2">
          <input
            type="range"
            min="0"
            max="100"
            value={timeStep}
            onChange={(e) => setTimeStep(Number(e.target.value))}
            className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
          <div className="flex justify-between text-[11px] text-slate-500 font-mono">
            <span>08:00 (Opening)</span>
            <span>12:00 (Lunch Rush)</span>
            <span>16:00 (Prep)</span>
            <span>20:00 (Dinner Peak)</span>
            <span className="text-emerald-400 font-bold">23:14 (NOW)</span>
          </div>
        </div>
      </div>

      {/* RDT State Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* World State Summary */}
        <div className="glass-panel p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Database className="w-5 h-5 text-emerald-400" />
              <span>Canonical World State Telemetry</span>
            </h2>
            <span className="text-xs text-slate-400">Upstream: MFE / IME</span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-xs text-slate-400 block">Total Active Visits</span>
              <span className="text-2xl font-extrabold text-white mt-1 block">24 Parties</span>
              <span className="text-[11px] text-emerald-400 mt-1 block">100% identity confidence</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-xs text-slate-400 block">Active Business Events</span>
              <span className="text-2xl font-extrabold text-white mt-1 block">7 Events</span>
              <span className="text-[11px] text-slate-400 mt-1 block">Seating, Ordering, Bussing</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-xs text-slate-400 block">Zone Capacity Ratio</span>
              <span className="text-2xl font-extrabold text-white mt-1 block">0.60 avg</span>
              <span className="text-[11px] text-slate-400 mt-1 block">Optimal comfort zone</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-xs text-slate-400 block">World Sync Latency</span>
              <span className="text-2xl font-extrabold text-emerald-400 mt-1 block">14.2 ms</span>
              <span className="text-[11px] text-slate-400 mt-1 block">Zero dropouts</span>
            </div>
          </div>
        </div>

        {/* JSON World Snapshot Export Preview */}
        <div className="glass-panel p-6 flex flex-col justify-between space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <FileCode className="w-5 h-5 text-teal-400" />
              <span>Serialized State Snapshot (JSON)</span>
            </h2>
            <span className="text-xs font-mono text-slate-500">v1.4.0-prod</span>
          </div>

          <div className="flex-1 bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto max-h-64">
            <pre>{JSON.stringify({
              timestamp: new Date().toISOString(),
              world_version: "RDT_PROD_2026",
              metrics: kpis,
              active_tables_count: tables.filter(t => t.status === 'OCCUPIED').length,
              sample_entity: tables[0]
            }, null, 2)}</pre>
          </div>
        </div>
      </div>
    </div>
  );
};
