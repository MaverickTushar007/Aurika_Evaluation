import React, { useEffect, useState } from 'react';
import { fetchBenchmarkLeaderboard, BenchmarkTrackerResult } from '../services/api';
import {
  FlaskConical,
  Trophy,
  Activity,
  CheckCircle2,
  TrendingUp,
  Download,
  Filter,
} from 'lucide-react';

export const ExperimentDashboard: React.FC = () => {
  const [leaderboard, setLeaderboard] = useState<BenchmarkTrackerResult[]>([]);

  useEffect(() => {
    fetchBenchmarkLeaderboard().then(setLeaderboard);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>AI Experimentation Laboratory & Failure Analysis</span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-normal">
              Research Laboratory
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Compare perception model architectures, multi-evidence fusion strategies, and historical benchmark leaderboards.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl border border-slate-700 text-xs font-semibold flex items-center gap-1.5">
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Leaderboard Table */}
      <div className="glass-panel overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center space-x-2">
            <Trophy className="w-5 h-5 text-amber-400" />
            <h2 className="text-base font-bold text-white">Tracking & ReID Benchmark Leaderboard</h2>
          </div>
          <span className="text-xs font-mono text-slate-400">Dataset: Aurika-Restaurant-Surveillance-v1</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-900 text-xs uppercase text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4 font-semibold">Rank & Tracker Name</th>
                <th className="py-3 px-4 font-semibold">Scenario / Difficulty</th>
                <th className="py-3 px-4 font-semibold text-right">MOTA ↑</th>
                <th className="py-3 px-4 font-semibold text-right">HOTA ↑</th>
                <th className="py-3 px-4 font-semibold text-right">IDF1 ↑</th>
                <th className="py-3 px-4 font-semibold text-right">ID Switches ↓</th>
                <th className="py-3 px-4 font-semibold text-right">FPS ↑</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {leaderboard.map((res, idx) => (
                <tr key={res.name} className={`hover:bg-slate-900/60 transition-colors ${idx === 0 ? 'bg-emerald-500/10 font-bold' : ''}`}>
                  <td className="py-3 px-4 flex items-center gap-2">
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                      idx === 0 ? 'bg-amber-500 text-slate-950 font-extrabold' : 'bg-slate-800 text-slate-400 font-mono'
                    }`}>
                      {idx + 1}
                    </span>
                    <span className={idx === 0 ? 'text-emerald-300 font-extrabold' : 'text-white font-semibold'}>{res.name}</span>
                    {idx === 0 && <span className="px-1.5 py-0.5 text-[10px] uppercase rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">SOTA</span>}
                  </td>
                  <td className="py-3 px-4 text-xs text-slate-400">{res.restaurantScenario}</td>
                  <td className="py-3 px-4 text-right font-mono text-white">{res.mota}%</td>
                  <td className="py-3 px-4 text-right font-mono text-emerald-400 font-bold">{res.hota}%</td>
                  <td className="py-3 px-4 text-right font-mono text-white">{res.idf1}%</td>
                  <td className="py-3 px-4 text-right font-mono text-rose-400">{res.identitySwitches}</td>
                  <td className="py-3 px-4 text-right font-mono text-teal-400">{res.fps}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Failure Analysis Highlight Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card">
          <h3 className="text-sm font-bold text-white mb-2">Severe Occlusion Robustness</h3>
          <p className="text-xs text-slate-300">
            Aurika MFE reduces identity switches by <strong className="text-emerald-400">89.4%</strong> compared to baseline ByteTrack during dining room peak hours when waiters occlude seated guests.
          </p>
        </div>
        <div className="glass-card">
          <h3 className="text-sm font-bold text-white mb-2">Visual Embedding Stability</h3>
          <p className="text-xs text-slate-300">
            Visual Identity Layer (VIL) maintains cosine similarity &gt;0.82 across illumination transitions (patio sunlight to dim dining room).
          </p>
        </div>
        <div className="glass-card">
          <h3 className="text-sm font-bold text-white mb-2">Real-Time Inference Speed</h3>
          <p className="text-xs text-slate-300">
            The complete perception pipeline executes at an average of <strong className="text-teal-400">29.8 FPS</strong> on edge NVIDIA TensorRT hardware.
          </p>
        </div>
      </div>
    </div>
  );
};
