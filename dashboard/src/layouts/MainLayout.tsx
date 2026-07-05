import React, { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Map,
  Layers,
  Sparkles,
  Bell,
  Users,
  GitGraph,
  BarChart3,
  FlaskConical,
  Trophy,
  FileText,
  Settings,
  LogOut,
  Moon,
  Sun,
  ShieldAlert,
  Activity,
  Menu,
  X,
  Video,
  TrendingUp,
  Brain,
  ShieldCheck,
  Rocket,
} from 'lucide-react';
import { useAuthStore } from '../state/useAuthStore';
import { useWorldStore } from '../state/useWorldStore';
import { wsClient } from '../websocket/wsClient';

export const MainLayout: React.FC = () => {
  const { user, logout } = useAuthStore();
  const { alerts, kpis, wsConnected } = useWorldStore();
  const [darkMode, setDarkMode] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showNotificationPanel, setShowNotificationPanel] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    wsClient.connect();
    return () => wsClient.disconnect();
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === 'k') {
          e.preventDefault();
          navigate('/floor-plan');
        } else if (e.key === 'd') {
          e.preventDefault();
          navigate('/');
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate]);

  const toggleTheme = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle('dark');
  };

  const unrenderedAlertsCount = alerts.filter((a) => !a.resolved).length;

  const navItems = [
    { name: 'Live Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Live Floor Plan', path: '/floor-plan', icon: Map },
    { name: 'Multi-Camera Hub', path: '/cameras', icon: Video },
    { name: 'Digital Twin View', path: '/digital-twin', icon: Layers },
    { name: 'Predictive Forecast', path: '/forecast', icon: TrendingUp },
    { name: 'Autonomous Learning', path: '/learning', icon: Brain },
    { name: 'Scientific Validation', path: '/validation', icon: ShieldCheck },
    { name: 'Pilot Deployment (PDRV)', path: '/pilot', icon: Rocket },
    { name: 'Recommendations', path: '/recommendations', icon: Sparkles, badge: useWorldStore.getState().recommendations.filter(r=>!r.acknowledged).length },
    { name: 'Alert Center', path: '/alerts', icon: Bell, badge: unrenderedAlertsCount },
    { name: 'Identity View', path: '/identities', icon: Users },
    { name: 'Global Graph View', path: '/graph', icon: GitGraph },
    { name: 'Analytics & Heatmaps', path: '/analytics', icon: BarChart3 },
    { name: 'Experiment Dashboard', path: '/experiments', icon: FlaskConical },
    { name: 'Benchmark Suite', path: '/benchmarks', icon: Trophy },
    { name: 'Operational Reports', path: '/reports', icon: FileText },
    { name: 'Platform Settings', path: '/settings', icon: Settings },
  ];

  return (
    <div className={`min-h-screen flex flex-col md:flex-row bg-slate-950 text-slate-100`}>
      {/* Sidebar */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-64 bg-slate-900/95 border-r border-slate-800 backdrop-blur-xl transition-transform duration-300 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0 md:w-20 lg:w-64'
        } flex flex-col`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <span className="font-bold text-slate-950 text-lg">A</span>
            </div>
            <span className={`font-bold text-lg tracking-wide bg-gradient-to-r from-emerald-400 to-teal-200 bg-clip-text text-transparent ${!sidebarOpen && 'md:hidden lg:inline'}`}>
              AURIKA OS
            </span>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="md:hidden text-slate-400 hover:text-white">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center px-3 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 group ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-inner'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                  }`
                }
              >
                <Icon className="w-5 h-5 flex-shrink-0 mr-3 group-hover:scale-110 transition-transform" />
                <span className={`${!sidebarOpen && 'md:hidden lg:inline'} truncate flex-1`}>{item.name}</span>
                {item.badge ? (
                  <span className={`px-2 py-0.5 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 ${!sidebarOpen && 'md:hidden lg:inline'}`}>
                    {item.badge}
                  </span>
                ) : null}
              </NavLink>
            );
          })}
        </nav>

        {/* User Profile Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/40">
          <div className="flex items-center justify-between">
            <div className={`flex items-center space-x-3 overflow-hidden ${!sidebarOpen && 'md:hidden lg:flex'}`}>
              <div className="w-9 h-9 rounded-full bg-emerald-600/30 border border-emerald-500 flex items-center justify-center font-bold text-emerald-300">
                {user?.name.charAt(0) || 'U'}
              </div>
              <div className="truncate">
                <p className="text-sm font-semibold text-white truncate">{user?.name}</p>
                <span className="inline-block px-2 py-0.5 text-[10px] uppercase font-bold rounded bg-slate-800 text-emerald-400 border border-slate-700">
                  {user?.role}
                </span>
              </div>
            </div>
            <button
              onClick={logout}
              title="Logout"
              className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Shell */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Navigation Bar */}
        <header className="h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-30">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            >
              <Menu className="w-6 h-6" />
            </button>
            <div className="flex items-center space-x-3">
              <span className="flex h-2.5 w-2.5 relative">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-amber-400'} opacity-75`}></span>
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${wsConnected ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
              </span>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {wsConnected ? 'Live Enterprise Stream' : 'Local Simulation Engine'} • FPS: <span className="text-emerald-400 font-mono">{kpis.inferenceFps}</span>
              </span>
            </div>
          </div>

          {/* Quick Actions & Notification Panel Toggle */}
          <div className="flex items-center space-x-3">
            <div className="hidden lg:flex items-center space-x-2 px-3 py-1 bg-slate-800/80 rounded-lg border border-slate-700/60 text-xs text-slate-400">
              <span>Shortcuts:</span>
              <kbd className="px-1.5 py-0.5 bg-slate-900 rounded border border-slate-700 text-slate-300 font-mono">⌘K</kbd>
              <span>Map</span>
              <kbd className="px-1.5 py-0.5 bg-slate-900 rounded border border-slate-700 text-slate-300 font-mono">⌘D</kbd>
              <span>Dashboard</span>
            </div>

            <button
              onClick={toggleTheme}
              className="p-2 rounded-xl bg-slate-800/60 border border-slate-700/80 text-slate-300 hover:text-white hover:bg-slate-800 transition-all"
            >
              {darkMode ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5 text-slate-300" />}
            </button>

            <div className="relative">
              <button
                onClick={() => setShowNotificationPanel(!showNotificationPanel)}
                className="p-2 rounded-xl bg-slate-800/60 border border-slate-700/80 text-slate-300 hover:text-white hover:bg-slate-800 transition-all relative"
              >
                <Bell className="w-5 h-5" />
                {unrenderedAlertsCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-rose-500 text-white font-bold text-[10px] flex items-center justify-center animate-pulse">
                    {unrenderedAlertsCount}
                  </span>
                )}
              </button>

              {/* Notification Popover */}
              {showNotificationPanel && (
                <div className="absolute right-0 mt-3 w-80 md:w-96 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl z-50 overflow-hidden">
                  <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
                    <div className="flex items-center space-x-2">
                      <ShieldAlert className="w-5 h-5 text-rose-400" />
                      <h3 className="font-semibold text-sm">Live System Alerts</h3>
                    </div>
                    <span className="text-xs text-slate-400">{unrenderedAlertsCount} active</span>
                  </div>
                  <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/60 p-2">
                    {alerts.length === 0 ? (
                      <p className="p-4 text-center text-xs text-slate-500">No active alerts reported.</p>
                    ) : (
                      alerts.slice(0, 5).map((a) => (
                        <div key={a.id} className="p-3 hover:bg-slate-800/40 rounded-xl transition-colors">
                          <div className="flex items-center justify-between mb-1">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                              a.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                              a.severity === 'WARNING' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                              'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                            }`}>
                              {a.severity}
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono">{a.timestamp}</span>
                          </div>
                          <p className="text-xs font-semibold text-slate-200">{a.title}</p>
                          <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">{a.description}</p>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="p-2 border-t border-slate-800 bg-slate-950/40 text-center">
                    <button
                      onClick={() => { setShowNotificationPanel(false); navigate('/alerts'); }}
                      className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition-colors"
                    >
                      View All Alerts & History →
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page Content Body */}
        <main className="flex-1 overflow-y-auto p-6 bg-slate-950">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
