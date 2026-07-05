import React, { useState } from 'react';
import {
  Users,
  Search,
  Calendar,
  Clock,
  ShieldCheck,
  UserCheck,
  Activity,
  History,
  GitCommit,
  Sparkles,
} from 'lucide-react';

interface GuestIdentity {
  id: string;
  canonicalName: string;
  type: 'VIP GUEST' | 'REGULAR GUEST' | 'STAFF / WAITER' | 'FIRST-TIME VISITOR';
  totalVisits: number;
  lastSeen: string;
  confidence: number;
  avgDurationMinutes: number;
  preferredTable?: string;
  journey: { time: string; event: string; zone: string; confidence: number }[];
}

const MOCK_IDENTITIES: GuestIdentity[] = [
  {
    id: 'IME-UUID-4091',
    canonicalName: 'Jonathan Davis (VIP)',
    type: 'VIP GUEST',
    totalVisits: 14,
    lastSeen: '10 mins ago (Table 201)',
    confidence: 0.99,
    avgDurationMinutes: 65,
    preferredTable: 'Table 201 (VIP Section)',
    journey: [
      { time: '17:45', event: 'Entered through Front Entrance', zone: 'Host Stand / Entrance', confidence: 0.98 },
      { time: '17:48', event: 'Seated at Table 201 by Host', zone: 'VIP Dining Section', confidence: 0.99 },
      { time: '18:15', event: 'Order placed with Waiter Marco R.', zone: 'VIP Dining Section', confidence: 0.99 },
      { time: '19:02', event: 'Payment completed via POS #04', zone: 'VIP Dining Section', confidence: 1.00 },
    ],
  },
  {
    id: 'IME-UUID-4092',
    canonicalName: 'Sophie Laurent (Staff)',
    type: 'STAFF / WAITER',
    totalVisits: 142,
    lastSeen: 'Active (Section 2)',
    confidence: 1.00,
    avgDurationMinutes: 380,
    preferredTable: 'Section 1 & 2 Station',
    journey: [
      { time: '15:30', event: 'Shift Clock-in at Staff Locker', zone: 'Back-of-House / Kitchen', confidence: 1.00 },
      { time: '16:00', event: 'Assigned to Dining Section 2', zone: 'Main Dining Room', confidence: 0.99 },
      { time: '17:15', event: 'Delivered entrees to Table 103', zone: 'Main Dining Room', confidence: 0.98 },
    ],
  },
  {
    id: 'IME-UUID-4093',
    canonicalName: 'Guest Party #88 (Anon)',
    type: 'FIRST-TIME VISITOR',
    totalVisits: 1,
    lastSeen: '15 mins ago (Patio 302)',
    confidence: 0.91,
    avgDurationMinutes: 48,
    preferredTable: 'Patio 302',
    journey: [
      { time: '18:10', event: 'Detected in Host Queue', zone: 'Host Stand', confidence: 0.88 },
      { time: '18:22', event: 'Seated at Patio 302', zone: 'Patio Section', confidence: 0.92 },
    ],
  },
];

export const IdentityView: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedIdentity, setSelectedIdentity] = useState<GuestIdentity>(MOCK_IDENTITIES[0]);

  const filteredIdentities = MOCK_IDENTITIES.filter(
    (id) =>
      id.canonicalName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      id.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      id.type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>Identity Memory Engine (IME) Introspection</span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 font-normal">
              Canonical Identity
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Track temporary hypotheses vs. canonical persistent facts across visual embeddings and ReID fusion.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Identities Sidebar List (1 col) */}
        <div className="glass-panel p-4 space-y-4 flex flex-col max-h-[650px]">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
            <input
              type="text"
              placeholder="Search by name, UUID, or type..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white focus:outline-none focus:border-purple-500 transition-colors"
            />
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {filteredIdentities.map((id) => {
              const isSelected = selectedIdentity.id === id.id;
              return (
                <div
                  key={id.id}
                  onClick={() => setSelectedIdentity(id)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-purple-500/15 border-purple-500/60 shadow-md shadow-purple-950/20'
                      : 'bg-slate-900/60 border-slate-800 hover:bg-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                      id.type === 'VIP GUEST' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                      id.type === 'STAFF / WAITER' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' :
                      'bg-slate-800 text-slate-300 border border-slate-700'
                    }`}>
                      {id.type}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500">{id.id.split('-')[2]}</span>
                  </div>
                  <h3 className="text-sm font-bold text-white truncate">{id.canonicalName}</h3>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2">
                    <span>Visits: <strong className="text-slate-200">{id.totalVisits}</strong></span>
                    <span className="text-emerald-400 font-semibold">{Math.round(id.confidence * 100)}% Conf</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Identity Deep Dive (2 cols) */}
        <div className="lg:col-span-2 glass-panel p-6 space-y-6 flex flex-col justify-between">
          <div>
            {/* Identity Profile Banner */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-800 gap-4">
              <div className="flex items-center space-x-4">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-white font-extrabold text-xl shadow-lg shadow-purple-900/30">
                  {selectedIdentity.canonicalName.charAt(0)}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-extrabold text-white">{selectedIdentity.canonicalName}</h2>
                    <span className="text-xs font-mono text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/30">
                      {selectedIdentity.id}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 flex items-center gap-3">
                    <span className="flex items-center gap-1">
                      <History className="w-3.5 h-3.5 text-slate-500" />
                      <span>Total Visits: {selectedIdentity.totalVisits}</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      <span>Avg Duration: {selectedIdentity.avgDurationMinutes}m</span>
                    </span>
                  </p>
                </div>
              </div>

              <div className="bg-slate-950/80 px-4 py-3 rounded-xl border border-slate-800 text-center sm:text-right">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">MFE Posterior Confidence</span>
                <span className="text-2xl font-extrabold text-emerald-400">{Math.round(selectedIdentity.confidence * 100)}%</span>
              </div>
            </div>

            {/* Visit Journey Timeline */}
            <div className="mt-6 space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-purple-400" />
                <span>Synchronized Visit Journey & Spatial Trajectory</span>
              </h3>

              <div className="relative pl-6 border-l-2 border-slate-800 space-y-6 my-4">
                {selectedIdentity.journey.map((step, idx) => (
                  <div key={idx} className="relative group">
                    <div className="absolute -left-[31px] top-0 w-3.5 h-3.5 rounded-full bg-purple-500 border-4 border-slate-950 group-hover:scale-125 transition-transform" />
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-colors">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-mono text-purple-400 font-bold">{step.time}</span>
                        <span className="text-[11px] text-slate-400 font-semibold">Zone: {step.zone}</span>
                      </div>
                      <p className="text-sm font-semibold text-slate-200">{step.event}</p>
                      <span className="inline-block mt-1 text-[10px] text-emerald-400 font-mono">
                        Visual Embedding Match Conf: {Math.round(step.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs text-purple-200 flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-purple-400 flex-shrink-0 mt-0.5" />
            <div>
              <strong className="text-white">Relational Note:</strong> This canonical identity is linked to 3 historical reservation records and linked to Waiter Marco R. with 98% preference frequency.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
