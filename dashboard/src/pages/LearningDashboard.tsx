import React, { useState } from 'react';
import { 
  Brain, ShieldCheck, AlertTriangle, Layers, RefreshCw, 
  FileText, CheckCircle2, TrendingUp, Database, Sliders, Play, 
  Activity, Sparkles, XCircle, ArrowUpRight, History
} from 'lucide-react';

interface ReviewItem {
  id: string;
  queueType: string;
  title: string;
  description: string;
  priorityScore: number;
  uncertainty: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
}

interface ModelCard {
  id: string;
  version: string;
  type: string;
  status: 'PRODUCTION' | 'CANDIDATE' | 'ARCHIVED';
  metrics: string;
  changelog: string;
}

const INITIAL_REVIEW_ITEMS: ReviewItem[] = [
  { id: 'REV-ID-101', queueType: 'IDENTITY_REVIEW', title: 'ID Switch on VIP Table 12', description: 'Track #442 switched ID after occlusion by service pillar during dinner rush.', priorityScore: 0.94, uncertainty: 0.85, status: 'PENDING' },
  { id: 'REV-MOD-202', queueType: 'MODEL_PROMOTION', title: 'Candidate Model: PERCEPTION_DETECTOR v1.1.0-cand', description: 'Trained on 450 new ReID crops. mAP +2.1%, FPS stable at 54. Requires human approval.', priorityScore: 0.95, uncertainty: 0.20, status: 'PENDING' },
  { id: 'REV-PRED-303', queueType: 'PREDICTION_REVIEW', title: 'Queue Wait Time MAPE Spike (+15m)', description: 'Sudden tour bus arrival caused temporary 12% error in 30m horizon forecast.', priorityScore: 0.78, uncertainty: 0.65, status: 'PENDING' },
  { id: 'REV-REC-404', queueType: 'RECOMMENDATION_REVIEW', title: 'Rejected Action: Open Overflow Patio', description: 'Operator manually rejected patio opening due to sudden rain storm.', priorityScore: 0.72, uncertainty: 0.50, status: 'PENDING' }
];

const INITIAL_MODELS: ModelCard[] = [
  { id: 'MOD-PERC-01', version: 'v1.0.0-prod', type: 'PERCEPTION_DETECTOR', status: 'PRODUCTION', metrics: 'mAP: 78.5% | FPS: 55.0', changelog: 'Baseline production ByteTrack/YOLOv8 perception engine' },
  { id: 'MOD-PERC-02', version: 'v1.1.0-cand', type: 'PERCEPTION_DETECTOR', status: 'CANDIDATE', metrics: 'mAP: 80.6% | FPS: 54.2', changelog: 'Trained on active learning high-value ID switch dataset (DS-YOLO-01)' },
  { id: 'MOD-PRED-01', version: 'v1.0.0-prod', type: 'QUEUE_FORECASTER', status: 'PRODUCTION', metrics: 'MAPE: 6.4% | RMSE: 1.8', changelog: 'Baseline production Holt-Winters & Erlang C queue forecaster' },
  { id: 'MOD-PRED-02', version: 'v0.9.5-old', type: 'QUEUE_FORECASTER', status: 'ARCHIVED', metrics: 'MAPE: 12.8% | RMSE: 3.4', changelog: 'Legacy static heuristics queue estimator' }
];

export const LearningDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'queue' | 'registry' | 'drift' | 'outcomes'>('queue');
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>(INITIAL_REVIEW_ITEMS);
  const [models, setModels] = useState<ModelCard[]>(INITIAL_MODELS);
  const [isCurating, setIsCurating] = useState<boolean>(false);

  const handleDecision = (id: string, decision: 'APPROVED' | 'REJECTED') => {
    setReviewItems(prev => prev.map(item => {
      if (item.id === id) {
        // If candidate model approved, promote in registry!
        if (item.queueType === 'MODEL_PROMOTION' && decision === 'APPROVED') {
          setModels(mods => mods.map(m => {
            if (m.version === 'v1.1.0-cand') return { ...m, status: 'PRODUCTION' };
            if (m.version === 'v1.0.0-prod' && m.type === 'PERCEPTION_DETECTOR') return { ...m, status: 'ARCHIVED' };
            return m;
          }));
          alert("✓ HUMAN APPROVAL VERIFIED: Candidate model v1.1.0-cand promoted to PRODUCTION!");
        }
        return { ...item, status: decision };
      }
      return item;
    }));
  };

  const handleRollback = (type: string, targetVersion: string) => {
    setModels(mods => mods.map(m => {
      if (m.type === type && m.version === targetVersion) return { ...m, status: 'PRODUCTION' };
      if (m.type === type && m.status === 'PRODUCTION') return { ...m, status: 'ARCHIVED' };
      return m;
    }));
    alert(`✓ 1-CLICK ROLLBACK EXECUTED: Restored ${type} to version ${targetVersion}!`);
  };

  const handleCurateDataset = () => {
    setIsCurating(true);
    setTimeout(() => {
      setIsCurating(false);
      alert("✓ DATASET BUILDER COMPLETE: Generated 450 new training samples formatted as YOLO, COCO, MOT, ReID, and Parquet!");
    }, 800);
  };

  return (
    <div className="space-y-6 animate-fade-in p-6 bg-slate-950 min-h-screen text-slate-100 font-sans">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-purple-950/70 via-indigo-950/50 to-slate-900/90 p-6 rounded-2xl border border-purple-500/30 backdrop-blur-md shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-purple-500/20 rounded-xl border border-purple-400/30">
            <Brain className="w-7 h-7 text-purple-400 animate-pulse" />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-white via-purple-200 to-indigo-300 bg-clip-text text-transparent">
              Autonomous Learning & Continuous Improvement Platform
            </h1>
            <p className="text-sm text-slate-400">
              Project Aurika Phase 16 • Zero Auto-Deployment Guardrail • Active Learning Curation • 1-Click Rollback
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={handleCurateDataset}
            disabled={isCurating}
            className="px-4 py-2 text-xs font-bold rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-600/30 transition-all flex items-center gap-2"
          >
            {isCurating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
            {isCurating ? "Curating Datasets..." : "Build Training Datasets"}
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex bg-slate-900/80 p-1.5 rounded-xl border border-slate-800 w-fit">
        {(['queue', 'registry', 'drift', 'outcomes'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-5 py-2 rounded-lg text-xs font-bold capitalize transition-all flex items-center gap-2 ${
              activeTab === tab
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30 scale-105'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            {tab === 'queue' && <ShieldCheck className="w-3.5 h-3.5" />}
            {tab === 'registry' && <Layers className="w-3.5 h-3.5" />}
            {tab === 'drift' && <Activity className="w-3.5 h-3.5" />}
            {tab === 'outcomes' && <TrendingUp className="w-3.5 h-3.5" />}
            {tab === 'queue' ? 'Human Review Queue' : tab === 'registry' ? 'Model Registry & Rollback' : tab === 'drift' ? 'Drift & Dataset Health' : 'Business Outcomes KPIs'}
          </button>
        ))}
      </div>

      {/* Tab 1: Human Review & Active Learning Queue */}
      {activeTab === 'queue' && (
        <div className="space-y-4 animate-fade-in">
          <div className="flex items-center justify-between bg-slate-900/60 p-4 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2 text-sm font-semibold text-purple-300">
              <ShieldCheck className="w-5 h-5 text-emerald-400" /> Strict Human-In-The-Loop Safety Guardrail Active
            </div>
            <span className="text-xs text-slate-400">Zero models or datasets are promoted to production without operator sign-off</span>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {reviewItems.map((item) => (
              <div key={item.id} className="bg-gradient-to-r from-slate-900 via-slate-900/80 to-slate-950 p-5 rounded-2xl border border-slate-800 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2.5">
                    <span className="px-2.5 py-0.5 rounded text-xs font-black bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      {item.queueType.replace(/_/g, ' ')}
                    </span>
                    <span className="text-xs font-bold text-slate-400">ID: {item.id}</span>
                    <span className="text-xs font-extrabold text-amber-400">Priority Score: {(item.priorityScore * 100).toFixed(0)}%</span>
                  </div>
                  <h3 className="text-base font-bold text-white">{item.title}</h3>
                  <p className="text-xs text-slate-300">{item.description}</p>
                </div>

                <div className="flex items-center gap-3">
                  {item.status === 'PENDING' ? (
                    <>
                      <button
                        onClick={() => handleDecision(item.id, 'APPROVED')}
                        className="px-4 py-2 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/50 text-emerald-300 font-bold rounded-xl text-xs transition-all flex items-center gap-1.5 shadow-md"
                      >
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Approve & Promote
                      </button>
                      <button
                        onClick={() => handleDecision(item.id, 'REJECTED')}
                        className="px-4 py-2 bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/50 text-rose-300 font-bold rounded-xl text-xs transition-all flex items-center gap-1.5"
                      >
                        <XCircle className="w-4 h-4 text-rose-400" /> Reject / Discard
                      </button>
                    </>
                  ) : (
                    <span className={`px-4 py-2 rounded-xl text-xs font-black border ${
                      item.status === 'APPROVED' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                    }`}>
                      ✓ DECISION RECORDED: {item.status}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: Model Registry & Rollback Manager */}
      {activeTab === 'registry' && (
        <div className="space-y-6 animate-fade-in">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {models.map((mod) => (
              <div key={mod.id} className={`p-6 rounded-2xl border shadow-xl transition-all ${
                mod.status === 'PRODUCTION' ? 'bg-gradient-to-br from-indigo-950/40 via-slate-900 to-slate-950 border-indigo-500/50' : 'bg-slate-900/80 border-slate-800'
              }`}>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold text-purple-400 uppercase tracking-wider">{mod.type}</span>
                  <span className={`px-3 py-1 rounded-full text-xs font-black border ${
                    mod.status === 'PRODUCTION' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 animate-pulse' :
                    mod.status === 'CANDIDATE' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}>
                    {mod.status}
                  </span>
                </div>

                <h3 className="text-xl font-black text-white mb-1">{mod.version}</h3>
                <p className="text-xs font-semibold text-indigo-300 mb-3">{mod.metrics}</p>
                <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80 mb-4">{mod.changelog}</p>

                <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800/80">
                  {mod.status === 'ARCHIVED' && (
                    <button
                      onClick={() => handleRollback(mod.type, mod.version)}
                      className="px-3.5 py-1.5 bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/50 text-purple-300 font-bold rounded-lg text-xs transition-all flex items-center gap-1.5"
                    >
                      <History className="w-3.5 h-3.5" /> 1-Click Rollback to {mod.version}
                    </button>
                  )}
                  {mod.status === 'CANDIDATE' && (
                    <span className="text-xs font-semibold text-amber-400 flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" /> Awaiting Human Review Queue Approval
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Drift & Dataset Health Dashboard */}
      {activeTab === 'drift' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-fade-in">
          <div className="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
            <h3 className="text-base font-extrabold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-400" /> Environmental & Camera Drift
            </h3>
            <ul className="text-xs space-y-3 font-medium divide-y divide-slate-800/80">
              <li className="pt-2 flex justify-between items-center"><span>Camera Reprojection Error:</span> <span className="font-bold text-emerald-400">1.4 px (Normal)</span></li>
              <li className="pt-2 flex justify-between items-center"><span>Lighting Illumination Shift:</span> <span className="font-bold text-emerald-400">+4.2% luma (Normal)</span></li>
              <li className="pt-2 flex justify-between items-center"><span>Seasonal Traffic Skew:</span> <span className="font-bold text-amber-400">+18% dinner demand</span></li>
              <li className="pt-2 flex justify-between items-center"><span>Model Prediction MAPE:</span> <span className="font-bold text-emerald-400">6.4% (Optimal)</span></li>
            </ul>
          </div>

          <div className="md:col-span-2 bg-slate-900/80 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
            <h3 className="text-base font-extrabold text-white flex items-center gap-2">
              <Database className="w-5 h-5 text-purple-400" /> Multi-Format Curated Dataset Inventory
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800"><span className="text-xs text-slate-400 block">YOLO Detection</span><span className="text-xl font-black text-white">240 labels</span></div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800"><span className="text-xs text-slate-400 block">COCO Annotations</span><span className="text-xl font-black text-purple-300">1,850 bboxes</span></div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800"><span className="text-xs text-slate-400 block">MOT Challenge</span><span className="text-xl font-black text-indigo-300">12 sequences</span></div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800"><span className="text-xs text-slate-400 block">ReID Embeddings</span><span className="text-xl font-black text-emerald-300">4,200 crops</span></div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800"><span className="text-xs text-slate-400 block">CSV Tabular</span><span className="text-xl font-black text-amber-300">15,400 rows</span></div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800"><span className="text-xs text-slate-400 block">Apache Parquet</span><span className="text-xl font-black text-sky-300">2.4 MB compressed</span></div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Business Outcomes KPIs */}
      {activeTab === 'outcomes' && (
        <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 shadow-xl space-y-6 animate-fade-in">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-400" /> Continuous Learning Business Impact & Efficiency Gains (30-Day Window)
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="bg-gradient-to-br from-purple-950/50 to-slate-950 p-5 rounded-xl border border-purple-500/30">
              <span className="text-xs font-bold text-purple-300 uppercase block mb-1">Customer Wait Reduction</span>
              <div className="text-3xl font-black text-white">-28.5% <span className="text-xs font-normal text-slate-400">(-4.5 min avg)</span></div>
              <p className="text-xs text-slate-300 mt-2">Achieved via predictive queue overflow alerts & virtual SMS waitlist triggers.</p>
            </div>

            <div className="bg-gradient-to-br from-indigo-950/50 to-slate-950 p-5 rounded-xl border border-indigo-500/30">
              <span className="text-xs font-bold text-indigo-300 uppercase block mb-1">Staff Labor Efficiency</span>
              <div className="text-3xl font-black text-white">+18.4% <span className="text-xs font-normal text-slate-400">turnaround speed</span></div>
              <p className="text-xs text-slate-300 mt-2">Driven by proactive table busing & waiter workload balance index recommendations.</p>
            </div>

            <div className="bg-gradient-to-br from-emerald-950/50 to-slate-950 p-5 rounded-xl border border-emerald-500/30">
              <span className="text-xs font-bold text-emerald-300 uppercase block mb-1">Operator Acceptance Rate</span>
              <div className="text-3xl font-black text-emerald-300">94.2% <span className="text-xs font-normal text-slate-400">sign-off</span></div>
              <p className="text-xs text-slate-300 mt-2">High confidence recommendations with zero automated deployment interruptions.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default LearningDashboard;
