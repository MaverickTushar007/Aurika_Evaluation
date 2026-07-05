import React, { useState } from 'react';
import { Camera, ShieldCheck, Activity, Wifi, RefreshCw, Layers, ArrowRight, CheckCircle2, AlertTriangle, Play } from 'lucide-react';

interface CameraItem {
  id: string;
  name: string;
  zone: string;
  fps: number;
  latency: number;
  status: 'ONLINE' | 'DEGRADED' | 'OFFLINE';
  calibration: 'VERIFIED' | 'ESTIMATED' | 'UNCALIBRATED';
  coveragePct: number;
}

interface HandoverItem {
  id: string;
  canonicalId: string;
  sourceCam: string;
  targetCam: string;
  distance: number;
  timeDelta: number;
  similarity: number;
  confidence: number;
  timestamp: string;
}

export const MultiCameraView: React.FC = () => {
  const [isSimulating, setIsSimulating] = useState(false);
  const [cameras, setCameras] = useState<CameraItem[]>([
    { id: 'CAM-01-ENT', name: 'Front Entrance Stream', zone: 'Entrance / Lobby', fps: 30.0, latency: 18, status: 'ONLINE', calibration: 'VERIFIED', coveragePct: 98.2 },
    { id: 'CAM-02-QUE', name: 'Host Stand Surveillance', zone: 'Waiting Area / Host Queue', fps: 29.8, latency: 22, status: 'ONLINE', calibration: 'VERIFIED', coveragePct: 95.0 },
    { id: 'CAM-03-DIN', name: 'Main Dining Room Sensor', zone: 'Main Dining Room', fps: 30.0, latency: 24, status: 'ONLINE', calibration: 'VERIFIED', coveragePct: 92.4 },
    { id: 'CAM-04-CAS', name: 'POS Counter Camera', zone: 'Cashier / POS Station', fps: 30.0, latency: 19, status: 'ONLINE', calibration: 'VERIFIED', coveragePct: 96.8 },
    { id: 'CAM-05-EXT', name: 'Exit Door Feed', zone: 'Exit Corridor', fps: 29.9, latency: 21, status: 'ONLINE', calibration: 'VERIFIED', coveragePct: 99.1 },
  ]);

  const [handovers, setHandovers] = useState<HandoverItem[]>([
    { id: 'h-1', canonicalId: 'CANON-UUID-1000', sourceCam: 'CAM-01-ENT', targetCam: 'CAM-02-QUE', distance: 3.61, timeDelta: 5.0, similarity: 1.00, confidence: 0.87, timestamp: 'Just now' },
    { id: 'h-2', canonicalId: 'CANON-UUID-1000', sourceCam: 'CAM-02-QUE', targetCam: 'CAM-03-DIN', distance: 4.47, timeDelta: 5.0, similarity: 1.00, confidence: 0.86, timestamp: '12s ago' },
    { id: 'h-3', canonicalId: 'CANON-UUID-1000', sourceCam: 'CAM-03-DIN', targetCam: 'CAM-04-CAS', distance: 4.47, timeDelta: 5.0, similarity: 1.00, confidence: 0.86, timestamp: '28s ago' },
    { id: 'h-4', canonicalId: 'CANON-UUID-1000', sourceCam: 'CAM-04-CAS', targetCam: 'CAM-05-EXT', distance: 4.47, timeDelta: 5.0, similarity: 1.00, confidence: 0.86, timestamp: '45s ago' },
    { id: 'h-5', canonicalId: 'CANON-UUID-0994', sourceCam: 'CAM-01-ENT', targetCam: 'CAM-03-DIN', distance: 8.20, timeDelta: 11.0, similarity: 0.92, confidence: 0.79, timestamp: '2m ago' },
  ]);

  const handleRunSimulation = () => {
    setIsSimulating(true);
    setTimeout(() => {
      const newHandover: HandoverItem = {
        id: `h-${Date.now()}`,
        canonicalId: `CANON-UUID-${Math.floor(1000 + Math.random() * 900)}`,
        sourceCam: 'CAM-01-ENT',
        targetCam: 'CAM-02-QUE',
        distance: Number((3.0 + Math.random() * 2.0).toFixed(2)),
        timeDelta: 5.0,
        similarity: Number((0.90 + Math.random() * 0.09).toFixed(2)),
        confidence: Number((0.85 + Math.random() * 0.10).toFixed(2)),
        timestamp: 'Just now'
      };
      setHandovers((prev) => [newHandover, ...prev.slice(0, 7)]);
      setIsSimulating(false);
    }, 1200);
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/60 p-6 rounded-2xl border border-slate-800/80 backdrop-blur-xl">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              <Camera className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Multi-Camera Intelligence Hub</h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Real-time homography coordinate projection, cross-camera ReID handover audit trail, and spatial blind spot coverage analysis.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleRunSimulation}
            disabled={isSimulating}
            className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition-all shadow-lg shadow-emerald-600/20 disabled:opacity-50"
          >
            {isSimulating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            <span>{isSimulating ? 'Simulating Handover...' : 'Trigger Handover Simulation'}</span>
          </button>
        </div>
      </div>

      {/* KPI Overview Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Online Camera Streams</span>
            <Wifi className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold text-white">5 <span className="text-sm text-slate-400 font-normal">/ 5 online</span></div>
          <div className="flex items-center space-x-1.5 mt-2 text-xs text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>0 ms sync jitter alignment</span>
          </div>
        </div>

        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Floor Grid Coverage</span>
            <Layers className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold text-white">96.3%</div>
          <div className="flex items-center space-x-1.5 mt-2 text-xs text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>68.5% multi-view redundancy</span>
          </div>
        </div>

        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Unmonitored Blind Spots</span>
            <ShieldCheck className="w-4 h-4 text-teal-400" />
          </div>
          <div className="text-3xl font-bold text-white">0 <span className="text-sm text-slate-400 font-normal">zones</span></div>
          <div className="flex items-center space-x-1.5 mt-2 text-xs text-teal-300">
            <span>Complete perimeter security</span>
          </div>
        </div>

        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Active Handovers (1h)</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold text-white">142</div>
          <div className="flex items-center space-x-1.5 mt-2 text-xs text-emerald-400">
            <span>99.4% IDF1 identity preservation</span>
          </div>
        </div>
      </div>

      {/* Camera Network Registry */}
      <div className="bg-slate-900/60 p-6 rounded-2xl border border-slate-800/80 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Surveillance Camera Registry</h2>
            <p className="text-xs text-slate-400">Registered sensors, homography calibration status, and real-time network latency telemetry.</p>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            All Extrinsics Verified
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cameras.map((cam) => (
            <div key={cam.id} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-colors space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20">
                  {cam.id}
                </span>
                <span className="flex items-center space-x-1 text-xs text-emerald-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span>{cam.status}</span>
                </span>
              </div>
              <div>
                <h3 className="font-semibold text-sm text-white">{cam.name}</h3>
                <p className="text-xs text-slate-400">{cam.zone}</p>
              </div>
              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800/80 text-center text-xs">
                <div className="bg-slate-900 p-1.5 rounded">
                  <span className="block text-[10px] text-slate-500 uppercase">FPS</span>
                  <span className="font-mono text-slate-200 font-semibold">{cam.fps.toFixed(1)}</span>
                </div>
                <div className="bg-slate-900 p-1.5 rounded">
                  <span className="block text-[10px] text-slate-500 uppercase">Latency</span>
                  <span className="font-mono text-slate-200 font-semibold">{cam.latency} ms</span>
                </div>
                <div className="bg-slate-900 p-1.5 rounded">
                  <span className="block text-[10px] text-slate-500 uppercase">Coverage</span>
                  <span className="font-mono text-emerald-400 font-semibold">{cam.coveragePct}%</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Cross-Camera Handover Audit Trail */}
      <div className="bg-slate-900/60 p-6 rounded-2xl border border-slate-800/80 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Cross-Camera Handover Audit Trail</h2>
            <p className="text-xs text-slate-400">Probabilistic ReID embedding matching across camera exits and entrances.</p>
          </div>
          <span className="text-xs text-slate-400">Showing latest 5 events</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/80 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
              <tr>
                <th className="p-3">Canonical ID</th>
                <th className="p-3">Handover Transition</th>
                <th className="p-3">Spatial Distance</th>
                <th className="p-3">Time Delta</th>
                <th className="p-3">ReID Cosine Sim</th>
                <th className="p-3">Posterior Confidence</th>
                <th className="p-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {handovers.map((item) => (
                <tr key={item.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3 font-mono text-xs font-bold text-emerald-400">{item.canonicalId}</td>
                  <td className="p-3">
                    <div className="flex items-center space-x-2 text-xs font-medium">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">{item.sourceCam}</span>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-emerald-300">{item.targetCam}</span>
                    </div>
                  </td>
                  <td className="p-3 font-mono text-xs">{item.distance} m</td>
                  <td className="p-3 font-mono text-xs">{item.timeDelta} s</td>
                  <td className="p-3 font-mono text-xs text-teal-300 font-semibold">{item.similarity.toFixed(2)}</td>
                  <td className="p-3">
                    <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      {(item.confidence * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="p-3 text-xs text-slate-500 font-mono">{item.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default MultiCameraView;
