import React, { useState } from 'react';
import { useWorldStore, TableState } from '../state/useWorldStore';
import { useAuthStore } from '../state/useAuthStore';
import {
  Map,
  Users,
  CheckCircle2,
  Clock,
  Flame,
  AlertCircle,
  RefreshCw,
  Sparkles,
  Info,
  UserCheck,
} from 'lucide-react';

export const LiveFloorPlan: React.FC = () => {
  const { tables, kpis, updateTable } = useWorldStore();
  const { hasPermission } = useAuthStore();
  const [selectedTable, setSelectedTable] = useState<TableState | null>(tables[0] || null);
  const [activeZone, setActiveZone] = useState<string>('ALL');

  const canEdit = hasPermission(['Operator', 'Administrator']);

  const handleStatusChange = (status: TableState['status']) => {
    if (!selectedTable || !canEdit) return;
    const guests = status === 'OCCUPIED' ? selectedTable.capacity : 0;
    updateTable(selectedTable.id, status, guests);
    setSelectedTable({ ...selectedTable, status, guests });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>Live Interactive Floor Plan</span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-teal-500/20 text-teal-300 border border-teal-500/30">
              Surveillance Grid
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time table occupancy, guest movement, waiter section assignments, and queue dynamics.
          </p>
        </div>

        {/* Zone Filters */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 md:pb-0">
          {['ALL', 'MAIN DINING', 'VIP SECTION', 'PATIO', 'HOST STAND'].map((zone) => (
            <button
              key={zone}
              onClick={() => setActiveZone(zone)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition-all ${
                activeZone === zone
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                  : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-white hover:bg-slate-800'
              }`}
            >
              {zone}
            </button>
          ))}
        </div>
      </div>

      {/* Main Floor Plan Display & Inspector Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Floor Plan Grid (2 cols) */}
        <div className="lg:col-span-2 glass-panel p-6 relative overflow-hidden flex flex-col min-h-[500px]">
          {/* Legend Banner */}
          <div className="flex items-center justify-between flex-wrap gap-4 pb-4 mb-4 border-b border-slate-800 text-xs text-slate-400">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-emerald-500 border border-emerald-400"></span>
                <span>Available ({kpis.availableTables})</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-rose-500 border border-rose-400 animate-pulse"></span>
                <span>Occupied ({kpis.activeTables})</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-amber-500 border border-amber-400"></span>
                <span>Reserved</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-purple-500 border border-purple-400"></span>
                <span>Dirty / Bussing</span>
              </span>
            </div>
            <span className="text-slate-500 font-mono text-[11px]">Grid Resolution: 100x100m</span>
          </div>

          {/* SVG Map Container */}
          <div className="flex-1 relative bg-slate-950/80 rounded-2xl border border-slate-800/80 p-6 flex items-center justify-center overflow-hidden">
            {/* Background Grid Lines */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b15_1px,transparent_1px),linear-gradient(to_bottom,#1e293b15_1px,transparent_1px)] bg-[size:32px_32px]" />

            {/* Entrance & Queue Zone */}
            <div className="absolute bottom-4 left-4 p-3 rounded-xl bg-slate-900/90 border border-amber-500/30 text-center shadow-lg w-40">
              <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider block">Host Stand / Queue</span>
              <span className="text-lg font-extrabold text-white">{kpis.queueLength} parties</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">~{kpis.expectedWaitMinutes} min wait</span>
            </div>

            {/* Kitchen Zone */}
            <div className="absolute top-4 right-4 p-3 rounded-xl bg-slate-900/90 border border-rose-500/30 text-center shadow-lg w-44">
              <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider flex items-center justify-center gap-1">
                <Flame className="w-3.5 h-3.5 text-rose-500" />
                <span>Kitchen / Expo</span>
              </span>
              <span className="text-sm font-extrabold text-white mt-1 block">Load: {kpis.kitchenLoadPercent}%</span>
              <span className="text-[10px] text-slate-400 block">3 Chefs active</span>
            </div>

            {/* Tables Map Canvas */}
            <div className="w-full h-full relative min-h-[380px]">
              {tables.map((table) => {
                const isSelected = selectedTable?.id === table.id;
                let bgClass = 'bg-emerald-500/20 border-emerald-500 text-emerald-300 shadow-emerald-500/20';
                if (table.status === 'OCCUPIED') bgClass = 'bg-rose-500/20 border-rose-500 text-rose-300 shadow-rose-500/20 animate-pulse';
                else if (table.status === 'RESERVED') bgClass = 'bg-amber-500/20 border-amber-500 text-amber-300 shadow-amber-500/20';
                else if (table.status === 'DIRTY') bgClass = 'bg-purple-500/20 border-purple-500 text-purple-300 shadow-purple-500/20';

                return (
                  <div
                    key={table.id}
                    onClick={() => setSelectedTable(table)}
                    style={{ left: `${table.x}%`, top: `${table.y}%` }}
                    className={`absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer p-4 rounded-2xl border-2 font-semibold shadow-lg transition-all duration-300 hover:scale-110 flex flex-col items-center justify-center w-28 h-24 ${bgClass} ${
                      isSelected ? 'ring-4 ring-white/50 scale-105 z-20' : 'z-10'
                    }`}
                  >
                    <span className="text-xs font-extrabold text-white">{table.name}</span>
                    <span className="text-[10px] uppercase font-bold mt-0.5 opacity-90">{table.status}</span>
                    <div className="flex items-center gap-1 mt-1 text-slate-200 text-xs">
                      <Users className="w-3.5 h-3.5" />
                      <span>{table.guests}/{table.capacity}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Selected Table Inspector Panel (1 col) */}
        <div className="glass-panel p-6 flex flex-col justify-between space-y-6">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Info className="w-5 h-5 text-emerald-400" />
                <span>Table Telemetry Inspector</span>
              </h2>
              {selectedTable && (
                <span className="text-xs font-mono text-slate-400">ID: {selectedTable.id}</span>
              )}
            </div>

            {selectedTable ? (
              <div className="mt-6 space-y-4">
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Section Name:</span>
                    <span className="text-base font-bold text-white">{selectedTable.name}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Current Status:</span>
                    <span className={`px-2 py-0.5 text-xs font-bold uppercase rounded ${
                      selectedTable.status === 'OCCUPIED' ? 'bg-rose-500/20 text-rose-300' :
                      selectedTable.status === 'AVAILABLE' ? 'bg-emerald-500/20 text-emerald-300' :
                      selectedTable.status === 'RESERVED' ? 'bg-amber-500/20 text-amber-300' :
                      'bg-purple-500/20 text-purple-300'
                    }`}>
                      {selectedTable.status}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Seating Capacity:</span>
                    <span className="text-sm font-semibold text-slate-200">{selectedTable.guests} / {selectedTable.capacity} Guests</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Assigned Waiter:</span>
                    <span className="text-sm font-semibold text-emerald-400 flex items-center gap-1">
                      <UserCheck className="w-4 h-4" />
                      <span>{selectedTable.assignedWaiter || 'Unassigned'}</span>
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Coordinates:</span>
                    <span className="text-xs font-mono text-slate-400">({selectedTable.x}, {selectedTable.y})</span>
                  </div>
                </div>

                {/* Status Action Buttons */}
                <div className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block">Operator Interventions</span>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      disabled={!canEdit}
                      onClick={() => handleStatusChange('AVAILABLE')}
                      className={`py-2 px-3 rounded-xl text-xs font-bold transition-all ${
                        selectedTable.status === 'AVAILABLE'
                          ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                          : 'bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-50'
                      }`}
                    >
                      Set Available
                    </button>
                    <button
                      disabled={!canEdit}
                      onClick={() => handleStatusChange('OCCUPIED')}
                      className={`py-2 px-3 rounded-xl text-xs font-bold transition-all ${
                        selectedTable.status === 'OCCUPIED'
                          ? 'bg-rose-500 text-white shadow-lg shadow-rose-500/30'
                          : 'bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-50'
                      }`}
                    >
                      Set Occupied
                    </button>
                    <button
                      disabled={!canEdit}
                      onClick={() => handleStatusChange('RESERVED')}
                      className={`py-2 px-3 rounded-xl text-xs font-bold transition-all ${
                        selectedTable.status === 'RESERVED'
                          ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/30'
                          : 'bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-50'
                      }`}
                    >
                      Set Reserved
                    </button>
                    <button
                      disabled={!canEdit}
                      onClick={() => handleStatusChange('DIRTY')}
                      className={`py-2 px-3 rounded-xl text-xs font-bold transition-all ${
                        selectedTable.status === 'DIRTY'
                          ? 'bg-purple-500 text-white shadow-lg shadow-purple-500/30'
                          : 'bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-50'
                      }`}
                    >
                      Mark Dirty
                    </button>
                  </div>
                  {!canEdit && (
                    <p className="text-[11px] text-slate-500 text-center italic mt-1">Read-only role cannot mutate table state.</p>
                  )}
                </div>

                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-start gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span>AI Insight: Table 101 has average turnover of 38 minutes. Next availability estimated in ~14 mins.</span>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500 text-sm">
                Select a table on the map to inspect real-time telemetry.
              </div>
            )}
          </div>

          <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/80 text-[11px] text-slate-400">
            <p className="font-semibold text-slate-300 mb-1">Surveillance Telemetry Source:</p>
            <p>Visual Identity Layer (VIL) & Multi-Evidence Fusion Engine (MFE) synced via WebSocket event stream.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
