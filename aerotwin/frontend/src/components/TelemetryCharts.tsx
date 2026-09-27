import React, { useState } from 'react';
import { BarChart3 } from 'lucide-react';
import { TelemetryData } from '../types';

interface TelemetryChartsProps {
  telemetry: TelemetryData | null;
  twin: {
    expected: Record<string, number>;
    residuals: Record<string, number>;
  } | null;
}

export const TelemetryCharts: React.FC<TelemetryChartsProps> = ({ telemetry, twin }) => {
  const [viewMode, setViewMode] = useState<'measured' | 'expected' | 'residual'>('measured');

  const tel = {
    rpm: typeof telemetry?.rpm === 'number' ? telemetry.rpm : 1400,
    manifold_pressure_inhg: typeof telemetry?.manifold_pressure_inhg === 'number' ? telemetry.manifold_pressure_inhg : 29.92,
    mean_egt_c: typeof telemetry?.mean_egt_c === 'number' ? telemetry.mean_egt_c : 650,
    mean_cht_c: typeof telemetry?.mean_cht_c === 'number' ? telemetry.mean_cht_c : 120,
    oil_pressure_psi: typeof telemetry?.oil_pressure_psi === 'number' ? telemetry.oil_pressure_psi : 55,
    oil_temperature_c: typeof telemetry?.oil_temperature_c === 'number' ? telemetry.oil_temperature_c : 85,
    turbo_boost_psi: typeof telemetry?.turbo_boost_psi === 'number' ? telemetry.turbo_boost_psi : 0,
    vibration_g: typeof telemetry?.vibration_g === 'number' ? telemetry.vibration_g : 0.05,
    bus_voltage: typeof telemetry?.bus_voltage === 'number' ? telemetry.bus_voltage : 28.0,
    fuel_flow_gph: typeof telemetry?.fuel_flow_gph === 'number' ? telemetry.fuel_flow_gph : 4.5,
  };

  const exp = twin?.expected ?? {};
  const res = twin?.residuals ?? {};

  // Formatter based on active view mode
  const getDisplayValue = (key: string, measuredVal: number, unit: string) => {
    const val = typeof measuredVal === 'number' && !isNaN(measuredVal) ? measuredVal : 0;
    if (viewMode === 'expected') {
      const rawExp = exp[key];
      const v = typeof rawExp === 'number' ? rawExp : val;
      return `${v.toFixed(1)} ${unit}`;
    }
    if (viewMode === 'residual') {
      const rawRes = res[key];
      const r = typeof rawRes === 'number' ? rawRes : 0.0;
      const prefix = r > 0 ? '+' : '';
      return `${prefix}${r.toFixed(2)} σ`;
    }
    return `${val.toFixed(1)} ${unit}`;
  };

  const getResidualBadge = (key: string) => {
    const rawRes = res[key];
    const r = Math.abs(typeof rawRes === 'number' ? rawRes : 0.0);
    if (r >= 3.0) return 'text-rose-700 bg-rose-50 border-rose-200';
    if (r >= 1.5) return 'text-amber-800 bg-amber-50 border-amber-200';
    return 'text-slate-600 bg-slate-100 border-slate-200';
  };

  const channels = [
    { label: 'Engine Speed', key: 'rpm', val: tel.rpm, unit: 'RPM', max: 5800 },
    { label: 'Manifold (MAP)', key: 'manifold_pressure', val: tel.manifold_pressure_inhg, unit: 'inHg', max: 40 },
    { label: 'Mean EGT', key: 'egt', val: tel.mean_egt_c, unit: '°C', max: 850 },
    { label: 'Mean CHT', key: 'cht', val: tel.mean_cht_c, unit: '°C', max: 260 },
    { label: 'Oil Pressure', key: 'oil_pressure', val: tel.oil_pressure_psi, unit: 'psi', max: 90 },
    { label: 'Oil Temp', key: 'oil_temp', val: tel.oil_temperature_c, unit: '°C', max: 130 },
    { label: 'Turbo Boost', key: 'turbo_boost', val: tel.turbo_boost_psi, unit: 'psi', max: 12 },
    { label: 'Vibration', key: 'vibration', val: tel.vibration_g, unit: 'g', max: 0.5 },
    { label: 'Fuel Flow', key: 'fuel_flow', val: tel.fuel_flow_gph, unit: 'gph', max: 15 },
    { label: 'Bus Voltage', key: 'bus_voltage', val: tel.bus_voltage, unit: 'V', max: 32 },
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-col gap-3 shadow-xs">
      {/* Header and Mode Selector */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-blue-600" />
          <div>
            <h3 className="font-mono text-xs font-bold text-slate-800 uppercase tracking-wider">
              Engine Telemetry &amp; Physics Residual Decomposition
            </h3>
            <span className="text-[11px] text-slate-500 font-sans">
              Real-time sensor telemetry vs digital twin baseline calculations
            </span>
          </div>
        </div>

        {/* View Mode Toggle Buttons */}
        <div className="bg-slate-100 p-1 rounded-lg border border-slate-200 flex text-xs font-mono">
          <button
            onClick={() => setViewMode('measured')}
            className={`px-3 py-1.5 rounded-md font-bold transition-all ${
              viewMode === 'measured'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
            }`}
            title="Show Measured Raw Sensor Telemetry"
          >
            MEASURED
          </button>
          <button
            onClick={() => setViewMode('expected')}
            className={`px-3 py-1.5 rounded-md font-bold transition-all ${
              viewMode === 'expected'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
            }`}
            title="Show Digital Twin Expected Physics Value"
          >
            TWIN EXPECTED
          </button>
          <button
            onClick={() => setViewMode('residual')}
            className={`px-3 py-1.5 rounded-md font-bold transition-all ${
              viewMode === 'residual'
                ? 'bg-amber-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
            }`}
            title="Show Normalized Residual Drift (sigma standard deviations)"
          >
            RESIDUAL (σ)
          </button>
        </div>
      </div>

      {/* Grid of Telemetry Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {channels.map((ch) => (
          <div
            key={ch.label}
            className="bg-slate-50 p-3 rounded-lg border border-slate-200 hover:border-slate-300 transition-all flex flex-col justify-between"
          >
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
              <span className="font-semibold text-slate-700">{ch.label}</span>
              <span className={`px-1.5 py-0.2 rounded border text-[9px] font-bold ${getResidualBadge(ch.key)}`}>
                {typeof res[ch.key] === 'number' ? `${res[ch.key] > 0 ? '+' : ''}${res[ch.key].toFixed(1)}σ` : '0.0σ'}
              </span>
            </div>

            <div className="my-2">
              <span className="text-xl font-mono font-black text-slate-900">
                {getDisplayValue(ch.key, ch.val, ch.unit)}
              </span>
            </div>

            {/* Micro progress gauge */}
            <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, Math.max(0, ((ch.val || 0) / (ch.max || 1)) * 100))}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TelemetryCharts;
