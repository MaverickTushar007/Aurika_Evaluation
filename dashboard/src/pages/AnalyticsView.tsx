import React, { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import { fetchHistoricalTrends, HistoricalTrendPoint } from '../services/api';
import {
  BarChart3,
  TrendingUp,
  Clock,
  Users,
  Calendar,
  Flame,
} from 'lucide-react';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export const AnalyticsView: React.FC = () => {
  const [trends, setTrends] = useState<HistoricalTrendPoint[]>([]);

  useEffect(() => {
    fetchHistoricalTrends().then(setTrends);
  }, []);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: { color: '#94a3b8', font: { family: 'Inter', size: 12 } },
      },
    },
    scales: {
      x: {
        grid: { color: '#1e293b' },
        ticks: { color: '#64748b' },
      },
      y: {
        grid: { color: '#1e293b' },
        ticks: { color: '#64748b' },
      },
    },
  };

  const occupancyData = {
    labels: trends.map((t) => t.time),
    datasets: [
      {
        label: 'Occupancy Count (Guests)',
        data: trends.map((t) => t.occupancy),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.15)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Queue Length (Parties)',
        data: trends.map((t) => t.queueLength),
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.15)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const waitTimeData = {
    labels: trends.map((t) => t.time),
    datasets: [
      {
        label: 'Expected Wait Time (Minutes)',
        data: trends.map((t) => t.waitMinutes),
        backgroundColor: '#3b82f6',
        borderRadius: 6,
      },
    ],
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>Operational Analytics & Utilization Heatmaps</span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-normal">
              Business Telemetry
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Historical KPIs, customer throughput trends, queue density, and table turnover analytics.
          </p>
        </div>
      </div>

      {/* Analytics Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass-card">
          <span className="text-xs text-slate-400 block uppercase font-bold">Avg Table Turnover</span>
          <span className="text-3xl font-extrabold text-white mt-1 block">42 Mins</span>
          <span className="text-[11px] text-emerald-400 flex items-center gap-1 mt-1">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>8% faster than industry benchmark</span>
          </span>
        </div>
        <div className="glass-card">
          <span className="text-xs text-slate-400 block uppercase font-bold">Daily Customer Throughput</span>
          <span className="text-3xl font-extrabold text-white mt-1 block">312 Guests</span>
          <span className="text-[11px] text-slate-400 block mt-1">Peak hour: 19:00 - 21:00</span>
        </div>
        <div className="glass-card">
          <span className="text-xs text-slate-400 block uppercase font-bold">Section Utilization Rate</span>
          <span className="text-3xl font-extrabold text-emerald-400 mt-1 block">84.2%</span>
          <span className="text-[11px] text-slate-400 block mt-1">Highest: Section 2 (Dining)</span>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-panel p-6 h-96 flex flex-col">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <Users className="w-4 h-4 text-emerald-400" />
            <span>Occupancy vs Queue Volume Over Time</span>
          </h3>
          <div className="flex-1">
            <Line options={chartOptions} data={occupancyData} />
          </div>
        </div>

        <div className="glass-panel p-6 h-96 flex flex-col">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-400" />
            <span>Expected Host Stand Wait Time Trends</span>
          </h3>
          <div className="flex-1">
            <Bar options={chartOptions} data={waitTimeData} />
          </div>
        </div>
      </div>

      {/* Spatial Utilization Heatmap Section */}
      <div className="glass-panel p-6">
        <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
          <Flame className="w-4 h-4 text-rose-400" />
          <span>Restaurant Floor Utilization & Traffic Heatmap</span>
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-rose-500/20 border border-rose-500/40 text-center">
            <span className="text-xs font-bold text-rose-300 uppercase block">Main Dining Room</span>
            <span className="text-2xl font-extrabold text-white mt-1 block">94%</span>
            <span className="text-[10px] text-rose-400 block mt-0.5">High Density Traffic</span>
          </div>
          <div className="p-4 rounded-xl bg-amber-500/20 border border-amber-500/40 text-center">
            <span className="text-xs font-bold text-amber-300 uppercase block">VIP Section</span>
            <span className="text-2xl font-extrabold text-white mt-1 block">72%</span>
            <span className="text-[10px] text-amber-400 block mt-0.5">Moderate Turnover</span>
          </div>
          <div className="p-4 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-center">
            <span className="text-xs font-bold text-emerald-300 uppercase block">Patio Outdoor</span>
            <span className="text-2xl font-extrabold text-white mt-1 block">45%</span>
            <span className="text-[10px] text-emerald-400 block mt-0.5">Available Capacity</span>
          </div>
          <div className="p-4 rounded-xl bg-rose-500/30 border border-rose-500/50 text-center animate-pulse">
            <span className="text-xs font-bold text-rose-300 uppercase block">Host Stand / Queue</span>
            <span className="text-2xl font-extrabold text-white mt-1 block">100%</span>
            <span className="text-[10px] text-rose-300 block mt-0.5">Bottleneck Zone</span>
          </div>
        </div>
      </div>
    </div>
  );
};
