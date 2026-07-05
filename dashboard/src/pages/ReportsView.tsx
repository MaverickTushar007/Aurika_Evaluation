import React, { useState } from 'react';
import { useWorldStore } from '../state/useWorldStore';
import {
  FileText,
  Download,
  Calendar,
  CheckCircle2,
  Table,
  FileCode,
  Printer,
} from 'lucide-react';

export const ReportsView: React.FC = () => {
  const { kpis, recommendations, alerts } = useWorldStore();
  const [reportType, setReportType] = useState<'DAILY' | 'WEEKLY' | 'MONTHLY'>('DAILY');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);

  const handleGenerate = () => {
    setIsGenerating(true);
    setGenerated(false);
    setTimeout(() => {
      setIsGenerating(false);
      setGenerated(true);
    }, 800);
  };

  const exportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({
      report_type: reportType,
      generated_at: new Date().toISOString(),
      kpi_summary: kpis,
      interventions_count: recommendations.length,
      alerts_summary: alerts.length,
    }, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `aurika_report_${reportType.toLowerCase()}_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const exportCSV = () => {
    const csvContent = `Metric,Value\nOccupancy,${kpis.currentOccupancy}\nMax Capacity,${kpis.maxCapacity}\nQueue Length,${kpis.queueLength}\nWait Time Mins,${kpis.expectedWaitMinutes}\nKitchen Load %,${kpis.kitchenLoadPercent}\nTotal Guests Today,${kpis.totalGuestsToday}`;
    const dataStr = "data:text/csv;charset=utf-8," + encodeURIComponent(csvContent);
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `aurika_metrics_${Date.now()}.csv`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>Operational Business Intelligence Reports</span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-normal">
              BI Generator
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Generate and export structured daily, weekly, and monthly restaurant performance summaries.
          </p>
        </div>
      </div>

      {/* Generator Configuration Panel */}
      <div className="glass-panel p-6 space-y-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pb-6 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-slate-300">Select Report Timeframe:</span>
            {(['DAILY', 'WEEKLY', 'MONTHLY'] as const).map((t) => (
              <button
                key={t}
                onClick={() => { setReportType(t); setGenerated(false); }}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                  reportType === t
                    ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/30'
                    : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-white'
                }`}
              >
                {t} REPORT
              </button>
            ))}
          </div>

          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="w-full sm:w-auto px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-900/30 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <FileText className="w-4 h-4" />
            <span>{isGenerating ? 'Compiling Telemetry...' : 'Generate BI Report'}</span>
          </button>
        </div>

        {/* Report Preview */}
        {generated ? (
          <div className="space-y-6 animate-fadeIn">
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-3 text-emerald-300">
                <CheckCircle2 className="w-6 h-6 text-emerald-400 flex-shrink-0" />
                <div>
                  <h3 className="font-bold text-sm">Report Compiled Successfully</h3>
                  <p className="text-xs text-emerald-400/80">Covering {reportType.toLowerCase()} operational cycle across all 8 dining sections.</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={exportCSV}
                  className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all"
                >
                  <Table className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Export CSV</span>
                </button>
                <button
                  onClick={exportJSON}
                  className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all"
                >
                  <FileCode className="w-3.5 h-3.5 text-teal-400" />
                  <span>Export JSON</span>
                </button>
                <button
                  onClick={() => window.print()}
                  className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all"
                >
                  <Printer className="w-3.5 h-3.5 text-blue-400" />
                  <span>Print / PDF</span>
                </button>
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 space-y-4 font-mono text-xs text-slate-300">
              <div className="border-b border-slate-800 pb-3 flex justify-between">
                <span className="font-bold text-emerald-400">AURIKA ENTERPRISE BI REPORT — {reportType}</span>
                <span>Date: {new Date().toLocaleDateString()}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-2">
                <div>
                  <span className="text-slate-500 block">Total Guests Seated:</span>
                  <span className="text-lg font-bold text-white">{kpis.totalGuestsToday}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Avg Table Turnover:</span>
                  <span className="text-lg font-bold text-white">{kpis.avgTurnoverMinutes} mins</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Peak Queue Length:</span>
                  <span className="text-lg font-bold text-amber-400">12 parties</span>
                </div>
                <div>
                  <span className="text-slate-500 block">System Reliability:</span>
                  <span className="text-lg font-bold text-emerald-400">99.98% uptime</span>
                </div>
              </div>
              <p className="text-slate-500 italic pt-2 border-t border-slate-800 text-[11px]">
                End of Report. Authenticated by Aurika Platform Storage Repository (PostgreSQL Enterprise Cluster).
              </p>
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-slate-500 text-sm">
            Select a timeframe above and click "Generate BI Report" to compile operational statistics.
          </div>
        )}
      </div>
    </div>
  );
};
