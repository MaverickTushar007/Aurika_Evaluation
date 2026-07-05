import React, { useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  Position,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  GitGraph,
  Users,
  Utensils,
  CreditCard,
  Filter,
  Sparkles,
} from 'lucide-react';

const initialNodes: Node[] = [
  {
    id: 'GUEST-1',
    type: 'default',
    data: { label: 'Jonathan Davis (VIP)' },
    position: { x: 100, y: 150 },
    style: { background: '#7e22ce', color: '#fff', border: '2px solid #a855f7', borderRadius: '12px', fontWeight: 'bold', padding: '10px' },
    sourcePosition: Position.Right,
  },
  {
    id: 'GUEST-2',
    type: 'default',
    data: { label: 'Guest Party #88' },
    position: { x: 100, y: 320 },
    style: { background: '#334155', color: '#fff', border: '2px solid #64748b', borderRadius: '12px', fontWeight: 'semibold', padding: '10px' },
    sourcePosition: Position.Right,
  },
  {
    id: 'TABLE-201',
    type: 'default',
    data: { label: 'Table 201 (VIP Section)' },
    position: { x: 400, y: 150 },
    style: { background: '#0f766e', color: '#fff', border: '2px solid #14b8a6', borderRadius: '12px', fontWeight: 'bold', padding: '12px' },
    targetPosition: Position.Left,
    sourcePosition: Position.Right,
  },
  {
    id: 'TABLE-302',
    type: 'default',
    data: { label: 'Patio Table 302' },
    position: { x: 400, y: 320 },
    style: { background: '#0f766e', color: '#fff', border: '2px solid #14b8a6', borderRadius: '12px', fontWeight: 'bold', padding: '12px' },
    targetPosition: Position.Left,
    sourcePosition: Position.Right,
  },
  {
    id: 'STAFF-1',
    type: 'default',
    data: { label: 'Waiter Marco R.' },
    position: { x: 700, y: 150 },
    style: { background: '#0369a1', color: '#fff', border: '2px solid #0ea5e9', borderRadius: '12px', fontWeight: 'bold', padding: '10px' },
    targetPosition: Position.Left,
  },
  {
    id: 'STAFF-2',
    type: 'default',
    data: { label: 'Waiter David K.' },
    position: { x: 700, y: 320 },
    style: { background: '#0369a1', color: '#fff', border: '2px solid #0ea5e9', borderRadius: '12px', fontWeight: 'bold', padding: '10px' },
    targetPosition: Position.Left,
  },
  {
    id: 'POS-04',
    type: 'default',
    data: { label: 'POS Terminal #04 ($145.50)' },
    position: { x: 400, y: 30 },
    style: { background: '#b45309', color: '#fff', border: '2px solid #f59e0b', borderRadius: '12px', fontSize: '12px', padding: '8px' },
    targetPosition: Position.Bottom,
  },
];

const initialEdges: Edge[] = [
  {
    id: 'e1',
    source: 'GUEST-1',
    target: 'TABLE-201',
    label: 'SEATED_AT (Conf: 0.99)',
    style: { stroke: '#a855f7', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#a855f7' },
  },
  {
    id: 'e2',
    source: 'TABLE-201',
    target: 'STAFF-1',
    label: 'SERVED_BY',
    style: { stroke: '#0ea5e9', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#0ea5e9' },
  },
  {
    id: 'e3',
    source: 'GUEST-1',
    target: 'POS-04',
    label: 'PAID_VIA',
    style: { stroke: '#f59e0b', strokeDasharray: '5 5' },
  },
  {
    id: 'e4',
    source: 'GUEST-2',
    target: 'TABLE-302',
    label: 'SEATED_AT (Conf: 0.92)',
    style: { stroke: '#64748b', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
  },
  {
    id: 'e5',
    source: 'TABLE-302',
    target: 'STAFF-2',
    label: 'SERVED_BY',
    style: { stroke: '#0ea5e9', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#0ea5e9' },
  },
];

export const GlobalGraphView: React.FC = () => {
  const [nodes] = useState<Node[]>(initialNodes);
  const [edges] = useState<Edge[]>(initialEdges);
  const [filterType, setFilterType] = useState<string>('ALL');

  return (
    <div className="space-y-6 h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>Global Identity Graph (GIG) Network Explorer</span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-normal">
              Relational Graph
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Interactive relational intelligence graph modeling Guests, Staff, Tables, Kitchen, and POS transactions.
          </p>
        </div>

        {/* Filter Toolbar */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          {['ALL', 'GUESTS ONLY', 'STAFF ONLY', 'TABLE LINKAGES'].map((f) => (
            <button
              key={f}
              onClick={() => setFilterType(f)}
              className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
                filterType === f
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/30'
                  : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-white'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* React Flow Canvas */}
      <div className="flex-1 glass-panel relative overflow-hidden rounded-2xl border border-slate-800">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          attributionPosition="bottom-right"
          className="bg-slate-950/80"
        >
          <Background color="#334155" gap={24} size={1} />
          <Controls className="bg-slate-900 border border-slate-700 rounded-xl fill-slate-300 shadow-xl overflow-hidden" />
        </ReactFlow>

        <div className="absolute top-4 left-4 z-10 p-3 rounded-xl bg-slate-900/90 border border-slate-800 backdrop-blur-md shadow-xl text-xs space-y-2">
          <span className="font-bold text-slate-300 block border-b border-slate-800 pb-1">Graph Entity Key</span>
          <div className="flex items-center gap-2 text-purple-300">
            <span className="w-3 h-3 rounded bg-purple-600 inline-block"></span>
            <span>Guest Identities</span>
          </div>
          <div className="flex items-center gap-2 text-teal-300">
            <span className="w-3 h-3 rounded bg-teal-600 inline-block"></span>
            <span>Tables / Seating</span>
          </div>
          <div className="flex items-center gap-2 text-sky-300">
            <span className="w-3 h-3 rounded bg-sky-600 inline-block"></span>
            <span>Staff / Waiters</span>
          </div>
          <div className="flex items-center gap-2 text-amber-300">
            <span className="w-3 h-3 rounded bg-amber-600 inline-block"></span>
            <span>POS / Transactions</span>
          </div>
        </div>
      </div>
    </div>
  );
};
