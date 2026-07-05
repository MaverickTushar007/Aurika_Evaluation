import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '../src/state/useAuthStore';
import { useWorldStore } from '../src/state/useWorldStore';

describe('Aurika OS State Stores Unit Tests', () => {
  beforeEach(() => {
    useAuthStore.setState({
      token: 'mock-token',
      user: { id: '1', name: 'Admin', email: 'admin@aurika.ai', role: 'Administrator' },
      isAuthenticated: true,
    });
  });

  it('verifies Role-Based Access Control (RBAC) permissions correctly', () => {
    const { hasPermission } = useAuthStore.getState();
    expect(hasPermission(['Administrator'])).toBe(true);
    expect(hasPermission(['Operator'])).toBe(true); // Admin overrides

    useAuthStore.setState({
      user: { id: '2', name: 'Reader', email: 'read@aurika.ai', role: 'Read-only' },
    });
    expect(useAuthStore.getState().hasPermission(['Operator'])).toBe(false);
    expect(useAuthStore.getState().hasPermission(['Read-only'])).toBe(true);
  });

  it('updates live KPIs and table status in world store', () => {
    const world = useWorldStore.getState();
    const initialOccupancy = world.kpis.currentOccupancy;
    world.updateKPIs({ currentOccupancy: initialOccupancy + 5 });
    expect(useWorldStore.getState().kpis.currentOccupancy).toBe(initialOccupancy + 5);

    world.updateTable('T2', 'OCCUPIED', 4);
    const table2 = useWorldStore.getState().tables.find((t) => t.id === 'T2');
    expect(table2?.status).toBe('OCCUPIED');
    expect(table2?.guests).toBe(4);
  });

  it('acknowledges recommendations and adds new alerts', () => {
    const world = useWorldStore.getState();
    const targetId = world.recommendations[0].id;
    expect(world.recommendations[0].acknowledged).toBe(false);

    world.acknowledgeRecommendation(targetId);
    expect(useWorldStore.getState().recommendations.find((r) => r.id === targetId)?.acknowledged).toBe(true);

    const initialAlertsCount = world.alerts.length;
    world.addAlert({
      severity: 'CRITICAL',
      title: 'Test Anomaly',
      description: 'Test description',
      location: 'VIP Zone',
    });
    expect(useWorldStore.getState().alerts.length).toBe(initialAlertsCount + 1);
    expect(useWorldStore.getState().alerts[0].title).toBe('Test Anomaly');
  });
});
