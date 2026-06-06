import React, { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, BarChart, Bar, Legend
} from 'recharts';

const mockExperiments = [
  {
    id: 'exp-001',
    name: 'CPU Stress — Target API',
    fault: 'cpu_stress',
    verdict: 'passed',
    duration: 62.3,
    slo_breached: false,
    started_at: '2026-06-06 09:12',
  },
  {
    id: 'exp-002',
    name: 'Latency Injection — Target API',
    fault: 'latency_injection',
    verdict: 'failed',
    duration: 18.7,
    slo_breached: true,
    started_at: '2026-06-06 10:05',
  },
  {
    id: 'exp-003',
    name: 'Memory Pressure — Target Worker',
    fault: 'memory_pressure',
    verdict: 'passed',
    duration: 45.1,
    slo_breached: false,
    started_at: '2026-06-06 11:30',
  },
  {
    id: 'exp-004',
    name: 'Process Kill — Target API',
    fault: 'process_kill',
    verdict: 'aborted',
    duration: 4.2,
    slo_breached: false,
    started_at: '2026-06-06 12:00',
  },
];

const sloData = [
  { time: '0s', error_rate: 0.2, latency_p99: 120, availability: 99.8 },
  { time: '10s', error_rate: 0.5, latency_p99: 180, availability: 99.5 },
  { time: '20s', error_rate: 1.2, latency_p99: 320, availability: 98.8 },
  { time: '30s', error_rate: 6.5, latency_p99: 620, availability: 93.5 },
  { time: '40s', error_rate: 8.1, latency_p99: 780, availability: 91.9 },
  { time: '50s', error_rate: 3.2, latency_p99: 410, availability: 96.8 },
  { time: '60s', error_rate: 0.3, latency_p99: 130, availability: 99.7 },
];

const verdictColor = (verdict) => {
  if (verdict === 'passed') return '#22c55e';
  if (verdict === 'failed') return '#ef4444';
  if (verdict === 'aborted') return '#f59e0b';
  return '#6b7280';
};

const verdictBg = (verdict) => {
  if (verdict === 'passed') return '#dcfce7';
  if (verdict === 'failed') return '#fee2e2';
  if (verdict === 'aborted') return '#fef3c7';
  return '#f3f4f6';
};

const faultIcon = (fault) => {
  if (fault === 'cpu_stress') return '⚡';
  if (fault === 'latency_injection') return '🌐';
  if (fault === 'memory_pressure') return '💾';
  if (fault === 'process_kill') return '💀';
  return '🔥';
};

export default function Dashboard() {
  const [selected, setSelected] = useState(mockExperiments[1]);

  const passed = mockExperiments.filter(e => e.verdict === 'passed').length;
  const failed = mockExperiments.filter(e => e.verdict === 'failed').length;
  const aborted = mockExperiments.filter(e => e.verdict === 'aborted').length;

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', background: '#0f172a', minHeight: '100vh', color: '#e2e8f0', padding: '24px' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '28px' }}>
        <span style={{ fontSize: '28px' }}>🔥</span>
        <div>
          <h1 style={{ margin: 0, fontSize: '22px', fontWeight: '700', color: '#f8fafc' }}>ChaosProbe</h1>
          <p style={{ margin: 0, fontSize: '13px', color: '#64748b' }}>Chaos Engineering Framework — fault injection, SLO monitoring, auto-rollback</p>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px', background: '#0d2a1a', border: '1px solid #166534', borderRadius: '8px', padding: '6px 14px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#22c55e' }}></div>
          <span style={{ fontSize: '13px', color: '#22c55e' }}>API healthy</span>
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        {[
          { label: 'Total Experiments', value: mockExperiments.length, color: '#60a5fa' },
          { label: 'Passed', value: passed, color: '#22c55e' },
          { label: 'Failed', value: failed, color: '#ef4444' },
          { label: 'Aborted', value: aborted, color: '#f59e0b' },
        ].map((stat) => (
          <div key={stat.label} style={{ background: '#1e293b', borderRadius: '12px', padding: '20px', border: '1px solid #334155' }}>
            <p style={{ margin: '0 0 8px', fontSize: '12px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{stat.label}</p>
            <p style={{ margin: 0, fontSize: '32px', fontWeight: '700', color: stat.color }}>{stat.value}</p>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>

        {/* Experiment List */}
        <div style={{ background: '#1e293b', borderRadius: '12px', padding: '20px', border: '1px solid #334155' }}>
          <h2 style={{ margin: '0 0 16px', fontSize: '15px', fontWeight: '600', color: '#f1f5f9' }}>Experiment Runs</h2>
          {mockExperiments.map((exp) => (
            <div
              key={exp.id}
              onClick={() => setSelected(exp)}
              style={{
                padding: '12px',
                borderRadius: '8px',
                marginBottom: '8px',
                cursor: 'pointer',
                background: selected?.id === exp.id ? '#0f172a' : 'transparent',
                border: selected?.id === exp.id ? '1px solid #3b82f6' : '1px solid transparent',
                transition: 'all 0.15s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '18px' }}>{faultIcon(exp.fault)}</span>
                  <div>
                    <p style={{ margin: 0, fontSize: '13px', fontWeight: '500', color: '#f1f5f9' }}>{exp.name}</p>
                    <p style={{ margin: 0, fontSize: '11px', color: '#64748b' }}>{exp.started_at} · {exp.duration}s</p>
                  </div>
                </div>
                <span style={{
                  fontSize: '11px',
                  fontWeight: '600',
                  padding: '3px 10px',
                  borderRadius: '20px',
                  background: verdictBg(exp.verdict),
                  color: verdictColor(exp.verdict),
                  textTransform: 'uppercase',
                }}>
                  {exp.verdict}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Selected Experiment Detail */}
        <div style={{ background: '#1e293b', borderRadius: '12px', padding: '20px', border: '1px solid #334155' }}>
          <h2 style={{ margin: '0 0 4px', fontSize: '15px', fontWeight: '600', color: '#f1f5f9' }}>Experiment Detail</h2>
          {selected && (
            <>
              <p style={{ margin: '0 0 16px', fontSize: '12px', color: '#64748b' }}>{selected.id}</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                {[
                  { label: 'Fault Type', value: selected.fault.replace('_', ' ') },
                  { label: 'Duration', value: `${selected.duration}s` },
                  { label: 'SLO Breached', value: selected.slo_breached ? 'Yes' : 'No' },
                  { label: 'Verdict', value: selected.verdict.toUpperCase() },
                ].map((item) => (
                  <div key={item.label} style={{ background: '#0f172a', borderRadius: '8px', padding: '12px' }}>
                    <p style={{ margin: '0 0 4px', fontSize: '11px', color: '#64748b' }}>{item.label}</p>
                    <p style={{ margin: 0, fontSize: '14px', fontWeight: '600', color: verdictColor(selected.verdict) }}>{item.value}</p>
                  </div>
                ))}
              </div>

              {/* Timeline */}
              <h3 style={{ margin: '0 0 10px', fontSize: '13px', color: '#94a3b8' }}>Event Timeline</h3>
              {['experiment_started', 'steady_state_confirmed', 'fault_injection_started', 'fault_active', 'slo_breach_rollback', 'fault_recovered', 'experiment_completed'].map((event, i) => (
                <div key={event} style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                  <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: i === 4 && selected.slo_breached ? '#ef4444' : '#3b82f6', flexShrink: 0 }}></div>
                  <span style={{ fontSize: '12px', color: i === 4 && selected.slo_breached ? '#fca5a5' : '#94a3b8' }}>{event.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      {/* SLO Chart */}
      <div style={{ background: '#1e293b', borderRadius: '12px', padding: '20px', border: '1px solid #334155' }}>
        <h2 style={{ margin: '0 0 20px', fontSize: '15px', fontWeight: '600', color: '#f1f5f9' }}>SLO Metrics During Experiment — Latency Injection</h2>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={sloData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
            <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 12 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', color: '#e2e8f0' }} />
            <Legend />
            <Line type="monotone" dataKey="error_rate" stroke="#ef4444" strokeWidth={2} dot={false} name="Error Rate %" />
            <Line type="monotone" dataKey="latency_p99" stroke="#f59e0b" strokeWidth={2} dot={false} name="p99 Latency (ms)" />
            <Line type="monotone" dataKey="availability" stroke="#22c55e" strokeWidth={2} dot={false} name="Availability %" />
          </LineChart>
        </ResponsiveContainer>
        <div style={{ marginTop: '12px', padding: '10px 14px', background: '#450a0a', borderRadius: '8px', border: '1px solid #7f1d1d' }}>
          <span style={{ fontSize: '12px', color: '#fca5a5' }}>⚠ SLO breach detected at 30s — error rate 6.5% exceeded 5% threshold. Auto-rollback triggered.</span>
        </div>
      </div>

    </div>
  );
}