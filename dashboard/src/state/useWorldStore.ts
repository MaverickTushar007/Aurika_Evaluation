import { create } from 'zustand';

export interface TableState {
  id: string;
  name: string;
  capacity: number;
  status: 'AVAILABLE' | 'OCCUPIED' | 'RESERVED' | 'DIRTY';
  guests: number;
  assignedWaiter?: string;
  x: number; // Floor plan coordinates (0-100 grid)
  y: number;
}

export interface RecommendationItem {
  id: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  reason: string;
  expectedBenefit: string;
  confidence: number;
  businessImpact: string;
  evidence: string[];
  acknowledged: boolean;
  timestamp: string;
}

export interface AlertItem {
  id: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  title: string;
  description: string;
  location?: string;
  timestamp: string;
  resolved: boolean;
}

export interface KPIStats {
  currentOccupancy: number;
  maxCapacity: number;
  queueLength: number;
  expectedWaitMinutes: number;
  activeTables: number;
  availableTables: number;
  kitchenLoadPercent: number;
  staffAvailabilityPercent: number;
  inferenceFps: number;
  totalGuestsToday: number;
  avgTurnoverMinutes: number;
}

interface WorldState {
  kpis: KPIStats;
  tables: TableState[];
  recommendations: RecommendationItem[];
  alerts: AlertItem[];
  wsConnected: boolean;
  updateKPIs: (partial: Partial<KPIStats>) => void;
  updateTable: (tableId: string, status: TableState['status'], guests?: number) => void;
  addAlert: (alert: Omit<AlertItem, 'id' | 'timestamp' | 'resolved'>) => void;
  acknowledgeRecommendation: (id: string) => void;
  setWsConnected: (connected: boolean) => void;
}

const INITIAL_TABLES: TableState[] = [
  { id: 'T1', name: 'Table 101', capacity: 2, status: 'OCCUPIED', guests: 2, assignedWaiter: 'Marco R.', x: 20, y: 25 },
  { id: 'T2', name: 'Table 102', capacity: 4, status: 'AVAILABLE', guests: 0, x: 45, y: 25 },
  { id: 'T3', name: 'Table 103', capacity: 4, status: 'OCCUPIED', guests: 3, assignedWaiter: 'Sophie L.', x: 70, y: 25 },
  { id: 'T4', name: 'Table 201 (VIP)', capacity: 6, status: 'RESERVED', guests: 0, x: 20, y: 55 },
  { id: 'T5', name: 'Table 202', capacity: 4, status: 'DIRTY', guests: 0, x: 45, y: 55 },
  { id: 'T6', name: 'Table 203', capacity: 8, status: 'OCCUPIED', guests: 7, assignedWaiter: 'Marco R.', x: 70, y: 55 },
  { id: 'T7', name: 'Patio 301', capacity: 2, status: 'AVAILABLE', guests: 0, x: 30, y: 85 },
  { id: 'T8', name: 'Patio 302', capacity: 4, status: 'OCCUPIED', guests: 4, assignedWaiter: 'David K.', x: 60, y: 85 },
];

const INITIAL_RECOMMENDATIONS: RecommendationItem[] = [
  {
    id: 'REC-101',
    priority: 'HIGH',
    title: 'Dispatch Busser to Table 202',
    reason: 'Table 202 has been dirty for >8 minutes while Queue Length is rising (4 parties waiting).',
    expectedBenefit: '+1 Table available; reduces wait time by ~4.5 mins.',
    confidence: 0.94,
    businessImpact: 'High ($120 estimated immediate seating value)',
    evidence: ['Visual detector confirmed guests departed at 17:32', 'Queue sensor detected party of 4 waiting at host stand'],
    acknowledged: false,
    timestamp: 'Just now',
  },
  {
    id: 'REC-102',
    priority: 'MEDIUM',
    title: 'Reassign Waiter Sophie L. to Section 2',
    reason: 'Section 1 load is low (1 active table); Section 2 experiences bottleneck at Table 203.',
    expectedBenefit: 'Reduces guest order latency by 35%.',
    confidence: 0.88,
    businessImpact: 'Medium (Improves CSAT score)',
    evidence: ['Staff tracking pipeline shows Sophie L. idle in server station for 6 mins'],
    acknowledged: false,
    timestamp: '5 mins ago',
  },
];

const INITIAL_ALERTS: AlertItem[] = [
  {
    id: 'ALT-901',
    severity: 'WARNING',
    title: 'Queue Bottleneck Detected',
    description: 'Host stand queue exceeded threshold (>5 parties waiting). Consider opening Patio section.',
    location: 'Host Stand / Entrance Zone',
    timestamp: '2 mins ago',
    resolved: false,
  },
  {
    id: 'ALT-902',
    severity: 'INFO',
    title: 'VIP Guest Recognized by IME',
    description: 'Identity Memory Engine matched Track #402 to recurring VIP "Jonathan Davis" (Visit #14).',
    location: 'Main Dining Room',
    timestamp: '10 mins ago',
    resolved: false,
  },
];

export const useWorldStore = create<WorldState>((set) => ({
  kpis: {
    currentOccupancy: 48,
    maxCapacity: 80,
    queueLength: 5,
    expectedWaitMinutes: 12,
    activeTables: 4,
    availableTables: 3,
    kitchenLoadPercent: 78,
    staffAvailabilityPercent: 65,
    inferenceFps: 29.8,
    totalGuestsToday: 312,
    avgTurnoverMinutes: 42,
  },
  tables: INITIAL_TABLES,
  recommendations: INITIAL_RECOMMENDATIONS,
  alerts: INITIAL_ALERTS,
  wsConnected: false,

  updateKPIs: (partial) =>
    set((state) => ({
      kpis: { ...state.kpis, ...partial },
    })),

  updateTable: (tableId, status, guests) =>
    set((state) => ({
      tables: state.tables.map((t) =>
        t.id === tableId
          ? { ...t, status, guests: guests !== undefined ? guests : t.guests }
          : t
      ),
    })),

  addAlert: (alert) =>
    set((state) => ({
      alerts: [
        {
          ...alert,
          id: `ALT-${Math.floor(1000 + Math.random() * 9000)}`,
          timestamp: 'Just now',
          resolved: false,
        },
        ...state.alerts,
      ],
    })),

  acknowledgeRecommendation: (id) =>
    set((state) => ({
      recommendations: state.recommendations.map((r) =>
        r.id === id ? { ...r, acknowledged: true } : r
      ),
    })),

  setWsConnected: (wsConnected) => set({ wsConnected }),
}));
