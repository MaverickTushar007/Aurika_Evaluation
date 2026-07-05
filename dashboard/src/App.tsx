import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout';
import { LiveDashboard } from './pages/LiveDashboard';
import { LiveFloorPlan } from './pages/LiveFloorPlan';
import { DigitalTwinView } from './pages/DigitalTwinView';
import { RecommendationCenter } from './pages/RecommendationCenter';
import { AlertCenter } from './pages/AlertCenter';
import { IdentityView } from './pages/IdentityView';
import { GlobalGraphView } from './pages/GlobalGraphView';
import { AnalyticsView } from './pages/AnalyticsView';
import { ExperimentDashboard } from './pages/ExperimentDashboard';
import { BenchmarkDashboard } from './pages/BenchmarkDashboard';
import { ReportsView } from './pages/ReportsView';
import { SettingsView } from './pages/SettingsView';
import { MultiCameraView } from './pages/MultiCameraView';
import { ForecastDashboard } from './pages/ForecastDashboard';
import { LearningDashboard } from './pages/LearningDashboard';
import { ValidationDashboard } from './pages/ValidationDashboard';
import { PilotDashboard } from './pages/PilotDashboard';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<LiveDashboard />} />
          <Route path="floor-plan" element={<LiveFloorPlan />} />
          <Route path="cameras" element={<MultiCameraView />} />
          <Route path="digital-twin" element={<DigitalTwinView />} />
          <Route path="forecast" element={<ForecastDashboard />} />
          <Route path="learning" element={<LearningDashboard />} />
          <Route path="validation" element={<ValidationDashboard />} />
          <Route path="pilot" element={<PilotDashboard />} />
          <Route path="recommendations" element={<RecommendationCenter />} />
          <Route path="alerts" element={<AlertCenter />} />
          <Route path="identities" element={<IdentityView />} />
          <Route path="graph" element={<GlobalGraphView />} />
          <Route path="analytics" element={<AnalyticsView />} />
          <Route path="experiments" element={<ExperimentDashboard />} />
          <Route path="benchmarks" element={<BenchmarkDashboard />} />
          <Route path="reports" element={<ReportsView />} />
          <Route path="settings" element={<SettingsView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
