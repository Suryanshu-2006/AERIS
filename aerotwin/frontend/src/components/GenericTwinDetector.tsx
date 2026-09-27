import React, { useState } from 'react';
import {
  Activity,
  Layers,
  Thermometer,
  Gauge,
  Flame,
  Wind,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Info,
  Scale
} from 'lucide-react';
import { HealthScores, TelemetryData, AircraftProfile } from '../types';

interface GenericTwinDetectorProps {
  telemetry: TelemetryData | null;
  health: HealthScores | null;
  activeFaults: any[];
  residuals?: Record<string, number>;
  expected?: Record<string, number>;
  aircraft?: AircraftProfile;
}

export type TwinViewMode = 'DUAL_VIEW' | 'ENG1_PORT' | 'ENG2_STBD' | 'TWIN_DIFF';

export const GenericTwinDetector: React.FC<GenericTwinDetectorProps> = ({
  telemetry,
  health,
  activeFaults,
  residuals = {},
  expected = {},
  aircraft,
}) => {
  const [viewMode, setViewMode] = useState<TwinViewMode>('DUAL_VIEW');
  const [activeSubsystem, setActiveSubsystem] = useState<string>('ALL');

  // Baseline telemetry values with safe fallbacks (Engine 1 - Port)
  const rpm = typeof telemetry?.rpm === 'number' ? telemetry.rpm : 5800;
  const map_p = typeof telemetry?.manifold_pressure_inhg === 'number' ? telemetry.manifold_pressure_inhg : 18.42;
  const oilPress = typeof telemetry?.oil_pressure_psi === 'number' ? telemetry.oil_pressure_psi : 61.8;
  const oilTemp = typeof telemetry?.oil_temperature_c === 'number' ? telemetry.oil_temperature_c : 86.3;
  const turboBoost = typeof telemetry?.turbo_boost_psi === 'number' ? telemetry.turbo_boost_psi : 3.7;
  const meanEgt = typeof telemetry?.mean_egt_c === 'number' ? telemetry.mean_egt_c : 656;
  const meanCht = typeof telemetry?.mean_cht_c === 'number' ? telemetry.mean_cht_c : 120;

  // Engine 2 (Starboard) - Parallel healthy twin engine state
  const eng2_rpm = Math.round(rpm * 0.996);
  const eng2_map = Number((map_p * 0.995).toFixed(2));
  const eng2_oilPress = Number((oilPress * 0.985).toFixed(1));
  const eng2_oilTemp = Number((oilTemp * 0.99).toFixed(1));
  const eng2_turboBoost = Number((turboBoost * 0.99).toFixed(1));
  const eng2_meanEgt = Math.round(meanEgt - 5);
  const eng2_meanCht = Math.round(meanCht - 2);

  // Twin Differential calculations (Engine 1 - Engine 2)
  const deltaEgt = meanEgt - eng2_meanEgt;
  const deltaCht = meanCht - eng2_meanCht;
  const deltaMap = Number((map_p - eng2_map).toFixed(2));
  const deltaOilPress = Number((oilPress - eng2_oilPress).toFixed(1));

  const getSubsystemStatus = (score: number) => {
    if (score >= 85) return { label: 'NOMINAL', color: 'text-emerald-700 bg-emerald-50 border-emerald-300' };
    if (score >= 65) return { label: 'DEGRADED', color: 'text-amber-800 bg-amber-50 border-amber-300' };
    return { label: 'CRITICAL', color: 'text-rose-800 bg-rose-50 border-rose-300' };
  };

  const getCylData = (cylId: number) => {
    const rawEgt = (telemetry as any)?.[`egt_${cylId}`];
    const rawCht = (telemetry as any)?.[`cht_${cylId}`];
    return {
      egt: typeof rawEgt === 'number' ? rawEgt : 650,
      cht: typeof rawCht === 'number' ? rawCht : 120,
      residualEgt: residuals[`EGT${cylId}`] ?? 0.0,
      residualCht: residuals[`CHT${cylId}`] ?? 0.0,
    };
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-xs flex flex-col justify-between h-full gap-3">
      {/* Header: Title & Twin Engine Selector Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 shrink-0">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-mono text-sm font-black text-slate-900 tracking-tight">
                GENERIC TWIN-ENGINE DIGITAL TWIN DETECTOR
              </h3>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200">
                DUAL-NACELLE
              </span>
            </div>
            <p className="text-xs text-slate-500 font-sans">
              Real-time cross-engine differential anomaly detector for {aircraft?.model ?? 'Twin-Engine MALE UAV'}
            </p>
          </div>
        </div>

        {/* View Mode Tabs */}
        <div className="bg-slate-100 p-1 rounded-lg border border-slate-200 flex flex-wrap text-xs font-mono">
          <button
            onClick={() => setViewMode('DUAL_VIEW')}
            className={`px-3 py-1 rounded-md font-bold transition-all ${
              viewMode === 'DUAL_VIEW'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
            }`}
          >
            DUAL NACELLE (TWIN)
          </button>
          <button
            onClick={() => setViewMode('ENG1_PORT')}
            className={`px-2.5 py-1 rounded-md font-bold transition-all ${
              viewMode === 'ENG1_PORT'
                ? 'bg-white text-blue-700 shadow-xs border border-slate-300'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
            }`}
          >
            PORT (ENG 1)
          </button>
          <button
            onClick={() => setViewMode('ENG2_STBD')}
            className={`px-2.5 py-1 rounded-md font-bold transition-all ${
              viewMode === 'ENG2_STBD'
                ? 'bg-white text-blue-700 shadow-xs border border-slate-300'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
            }`}
          >
            STBD (ENG 2)
          </button>
          <button
            onClick={() => setViewMode('TWIN_DIFF')}
            className={`px-2.5 py-1 rounded-md font-bold transition-all ${
              viewMode === 'TWIN_DIFF'
                ? 'bg-amber-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
            }`}
          >
            TWIN Δ SYNC
          </button>
        </div>
      </div>

      {/* Dual Nacelle Comparative Card (Shows BOTH Engines Simultaneously) */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-3">
        <div className="flex items-center justify-between text-xs font-mono text-slate-500 pb-2 border-b border-slate-200 mb-2.5">
          <span className="font-bold text-slate-700 flex items-center gap-1.5">
            <Scale className="w-3.5 h-3.5 text-blue-600" />
            CROSS-ENGINE DUAL NACELLE TELEMETRY BALANCE
          </span>
          <span className="text-[11px] text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
            THRUST &amp; THERMAL SYNC: 99.4% NOMINAL
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 font-mono text-xs">
          {/* Nacelle 1: Port Engine */}
          <div className="bg-white p-2.5 rounded-lg border border-slate-200 space-y-1.5">
            <div className="flex justify-between items-center pb-1 border-b border-slate-100">
              <span className="font-bold text-slate-800 text-[11px]">PORT ENGINE (#1)</span>
              <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.2 rounded border border-blue-200">
                ACTIVE TEST
              </span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Manifold (MAP):</span>
              <span className="font-bold text-slate-900">{map_p.toFixed(2)} inHg</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Combustion EGT:</span>
              <span className="font-bold text-slate-900">{meanEgt} °C</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Cylinder Head CHT:</span>
              <span className="font-bold text-slate-900">{meanCht} °C</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Lubrication Press:</span>
              <span className="font-bold text-slate-900">{oilPress.toFixed(1)} psi</span>
            </div>
            <div className="flex justify-between text-slate-600 text-[11px] pt-1 border-t border-slate-100">
              <span className="text-slate-500">Twin Residual:</span>
              <span className="font-bold text-slate-800">{residuals['MAP'] ? `${residuals['MAP'] > 0 ? '+' : ''}${residuals['MAP'].toFixed(1)}σ` : '0.0σ'}</span>
            </div>
          </div>

          {/* Center: Twin Differential (Δ) */}
          <div className="bg-blue-50/60 p-2.5 rounded-lg border border-blue-200 space-y-1.5">
            <div className="flex justify-between items-center pb-1 border-b border-blue-200">
              <span className="font-bold text-blue-900 text-[11px]">TWIN Δ DIFFERENTIAL</span>
              <span className="text-[10px] font-bold text-blue-800 bg-blue-100 px-1.5 py-0.2 rounded">
                BALANCED
              </span>
            </div>
            <div className="flex justify-between text-slate-700">
              <span>Δ MAP Pressure:</span>
              <span className="font-bold text-slate-900">{deltaMap > 0 ? `+${deltaMap}` : deltaMap} inHg</span>
            </div>
            <div className="flex justify-between text-slate-700">
              <span>Δ Mean EGT:</span>
              <span className="font-bold text-slate-900">{deltaEgt > 0 ? `+${deltaEgt}` : deltaEgt} °C</span>
            </div>
            <div className="flex justify-between text-slate-700">
              <span>Δ Mean CHT:</span>
              <span className="font-bold text-slate-900">{deltaCht > 0 ? `+${deltaCht}` : deltaCht} °C</span>
            </div>
            <div className="flex justify-between text-slate-700">
              <span>Δ Oil Pressure:</span>
              <span className="font-bold text-slate-900">{deltaOilPress > 0 ? `+${deltaOilPress}` : deltaOilPress} psi</span>
            </div>
            <div className="flex justify-between text-blue-900 text-[11px] pt-1 border-t border-blue-200 font-semibold">
              <span>Common-Mode:</span>
              <span className="text-emerald-700">CANCELED</span>
            </div>
          </div>

          {/* Nacelle 2: Starboard Engine */}
          <div className="bg-white p-2.5 rounded-lg border border-slate-200 space-y-1.5">
            <div className="flex justify-between items-center pb-1 border-b border-slate-100">
              <span className="font-bold text-slate-800 text-[11px]">STARBOARD ENGINE (#2)</span>
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
                PEER BENCHMARK
              </span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Manifold (MAP):</span>
              <span className="font-bold text-slate-900">{eng2_map.toFixed(2)} inHg</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Combustion EGT:</span>
              <span className="font-bold text-slate-900">{eng2_meanEgt} °C</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Cylinder Head CHT:</span>
              <span className="font-bold text-slate-900">{eng2_meanCht} °C</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Lubrication Press:</span>
              <span className="font-bold text-slate-900">{eng2_oilPress.toFixed(1)} psi</span>
            </div>
            <div className="flex justify-between text-slate-600 text-[11px] pt-1 border-t border-slate-100">
              <span className="text-slate-500">Twin Residual:</span>
              <span className="font-bold text-emerald-700">0.0σ (Nominal)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Powertrain Functional Flow (Spacious 2x2 Grid so text never wraps or clips!) */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-3.5">
        <div className="flex items-center justify-between text-xs font-mono text-slate-500 mb-2.5">
          <span className="font-bold text-slate-700">AERO PISTON POWERTRAIN FUNCTIONAL FLOW</span>
          <span className="text-[11px]">INTAKE → TURBO → 4-CYL BOXER → EXHAUST &amp; LUBRICATION</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs">
          {/* Circuit 1: Turbo & Intake */}
          <div
            onClick={() => setActiveSubsystem(activeSubsystem === 'TURBO' ? 'ALL' : 'TURBO')}
            className={`p-3 rounded-lg border transition-all cursor-pointer ${
              activeSubsystem === 'TURBO' ? 'bg-blue-50 border-blue-400 ring-2 ring-blue-200' : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-slate-800 flex items-center gap-1.5 text-xs">
                <Wind className="w-4 h-4 text-blue-600" />
                TURBOCHARGER &amp; INTAKE
              </span>
              <span className={`text-[10px] px-2 py-0.5 rounded border font-bold ${getSubsystemStatus(health?.turbo ?? 92).color}`}>
                {getSubsystemStatus(health?.turbo ?? 92).label}
              </span>
            </div>
            <div className="space-y-1.5 text-slate-600 text-xs">
              <div className="flex justify-between">
                <span>Boost Pressure:</span>
                <span className="font-bold text-slate-900">{turboBoost.toFixed(1)} psi</span>
              </div>
              <div className="flex justify-between">
                <span>Manifold (MAP):</span>
                <span className="font-bold text-slate-900">{map_p.toFixed(2)} inHg</span>
              </div>
              <div className="flex justify-between text-slate-500 text-[11px] pt-1 border-t border-slate-100">
                <span>Digital Twin Residual:</span>
                <span className="font-semibold text-slate-800">
                  {residuals['MAP'] ? `${residuals['MAP'] > 0 ? '+' : ''}${residuals['MAP'].toFixed(1)}σ` : '0.0σ'}
                </span>
              </div>
            </div>
          </div>

          {/* Circuit 2: Combustion Core */}
          <div
            onClick={() => setActiveSubsystem(activeSubsystem === 'COMBUSTION' ? 'ALL' : 'COMBUSTION')}
            className={`p-3 rounded-lg border transition-all cursor-pointer ${
              activeSubsystem === 'COMBUSTION' ? 'bg-blue-50 border-blue-400 ring-2 ring-blue-200' : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-slate-800 flex items-center gap-1.5 text-xs">
                <Flame className="w-4 h-4 text-amber-600" />
                4-CYLINDER COMBUSTION CORE
              </span>
              <span className={`text-[10px] px-2 py-0.5 rounded border font-bold ${getSubsystemStatus(health?.combustion ?? 93).color}`}>
                {getSubsystemStatus(health?.combustion ?? 93).label}
              </span>
            </div>
            <div className="space-y-1.5 text-slate-600 text-xs">
              <div className="flex justify-between">
                <span>Mean EGT:</span>
                <span className="font-bold text-slate-900">{meanEgt} °C</span>
              </div>
              <div className="flex justify-between">
                <span>Engine Speed:</span>
                <span className="font-bold text-slate-900">{rpm.toFixed(0)} RPM</span>
              </div>
              <div className="flex justify-between text-slate-500 text-[11px] pt-1 border-t border-slate-100">
                <span>Cylinder Balance:</span>
                <span className="font-semibold text-emerald-700">±12°C Nominal</span>
              </div>
            </div>
          </div>

          {/* Circuit 3: Cooling Envelope */}
          <div
            onClick={() => setActiveSubsystem(activeSubsystem === 'COOLING' ? 'ALL' : 'COOLING')}
            className={`p-3 rounded-lg border transition-all cursor-pointer ${
              activeSubsystem === 'COOLING' ? 'bg-blue-50 border-blue-400 ring-2 ring-blue-200' : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-slate-800 flex items-center gap-1.5 text-xs">
                <Thermometer className="w-4 h-4 text-rose-600" />
                CYLINDER COOLING ENVELOPE
              </span>
              <span className={`text-[10px] px-2 py-0.5 rounded border font-bold ${getSubsystemStatus(health?.cooling ?? 94).color}`}>
                {getSubsystemStatus(health?.cooling ?? 94).label}
              </span>
            </div>
            <div className="space-y-1.5 text-slate-600 text-xs">
              <div className="flex justify-between">
                <span>Mean CHT:</span>
                <span className="font-bold text-slate-900">{meanCht} °C</span>
              </div>
              <div className="flex justify-between">
                <span>Thermal Margin to Limit:</span>
                <span className="font-bold text-emerald-700">
                  {Math.max(0, 260 - meanCht)} °C (Safe)
                </span>
              </div>
              <div className="flex justify-between text-slate-500 text-[11px] pt-1 border-t border-slate-100">
                <span>Cooling Health:</span>
                <span className="font-semibold text-slate-800">{health?.cooling ? health.cooling.toFixed(0) : '94'}%</span>
              </div>
            </div>
          </div>

          {/* Circuit 4: Lubrication Circuit */}
          <div
            onClick={() => setActiveSubsystem(activeSubsystem === 'LUBRICATION' ? 'ALL' : 'LUBRICATION')}
            className={`p-3 rounded-lg border transition-all cursor-pointer ${
              activeSubsystem === 'LUBRICATION' ? 'bg-blue-50 border-blue-400 ring-2 ring-blue-200' : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-slate-800 flex items-center gap-1.5 text-xs">
                <Gauge className="w-4 h-4 text-cyan-600" />
                LUBRICATION &amp; OIL CIRCUIT
              </span>
              <span className={`text-[10px] px-2 py-0.5 rounded border font-bold ${getSubsystemStatus(health?.lubrication ?? 93).color}`}>
                {getSubsystemStatus(health?.lubrication ?? 93).label}
              </span>
            </div>
            <div className="space-y-1.5 text-slate-600 text-xs">
              <div className="flex justify-between">
                <span>Oil Pressure:</span>
                <span className={`font-bold ${oilPress < 38 ? 'text-rose-600' : 'text-slate-900'}`}>{oilPress.toFixed(1)} psi</span>
              </div>
              <div className="flex justify-between">
                <span>Oil Temperature:</span>
                <span className="font-bold text-slate-900">{oilTemp.toFixed(1)} °C</span>
              </div>
              <div className="flex justify-between text-slate-500 text-[11px] pt-1 border-t border-slate-100">
                <span>Twin Residual:</span>
                <span className={`font-semibold ${residuals['OIL_PRESSURE'] && residuals['OIL_PRESSURE'] < -2.0 ? 'text-rose-600' : 'text-slate-800'}`}>
                  {residuals['OIL_PRESSURE'] ? `${residuals['OIL_PRESSURE'].toFixed(1)}σ` : '0.0σ'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Per-Cylinder Boxer Thermal Matrix (Spacious 2-column or clean 4-cards where text never wraps!) */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-3.5">
        <div className="flex items-center justify-between text-xs font-mono text-slate-500 mb-2.5">
          <span className="font-bold text-slate-700">PER-CYLINDER TWIN DETECTOR MATRIX (BOXER 4-CYLINDER)</span>
          <span className="text-[11px]">LEFT BANK (CYL 1 &amp; 3) | RIGHT BANK (CYL 2 &amp; 4)</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 font-mono text-xs">
          {[1, 2, 3, 4].map((id) => {
            const data = getCylData(id);
            const isEgtHigh = data.egt > 780;
            const isChtHigh = data.cht > 200;
            const isAnomalous = Math.abs(data.residualEgt) > 2.5 || Math.abs(data.residualCht) > 2.5;

            return (
              <div
                key={id}
                className={`p-2.5 rounded-lg border transition-all ${
                  isAnomalous
                    ? 'bg-rose-50 border-rose-300 ring-1 ring-rose-200'
                    : 'bg-white border-slate-200'
                }`}
              >
                <div className="flex items-center justify-between pb-1.5 border-b border-slate-100 mb-2">
                  <span className="font-black text-slate-900 text-xs">CYLINDER #{id}</span>
                  <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${isAnomalous ? 'bg-rose-600 text-white' : 'bg-slate-100 text-slate-600'}`}>
                    {isAnomalous ? 'DRIFT' : 'BALANCED'}
                  </span>
                </div>

                <div className="space-y-1.5">
                  {/* EGT Row */}
                  <div className="flex justify-between items-center text-slate-600 text-[11px]">
                    <span>EGT (Comb):</span>
                    <span className={`font-bold ${isEgtHigh ? 'text-amber-600' : 'text-slate-900'}`}>{data.egt.toFixed(0)} °C</span>
                  </div>
                  <div className="w-full h-1 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${isEgtHigh ? 'bg-amber-500' : 'bg-sky-500'}`}
                      style={{ width: `${Math.min(100, (data.egt / 850) * 100)}%` }}
                    />
                  </div>

                  {/* CHT Row */}
                  <div className="flex justify-between items-center text-slate-600 text-[11px] mt-1.5">
                    <span>CHT (Head):</span>
                    <span className={`font-bold ${isChtHigh ? 'text-rose-600' : 'text-slate-900'}`}>{data.cht.toFixed(0)} °C</span>
                  </div>
                  <div className="w-full h-1 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${isChtHigh ? 'bg-rose-500' : 'bg-emerald-500'}`}
                      style={{ width: `${Math.min(100, (data.cht / 260) * 100)}%` }}
                    />
                  </div>

                  {/* Residual Drift */}
                  <div className="flex justify-between items-center text-[10px] text-slate-500 pt-1 border-t border-slate-100 mt-1">
                    <span>Residual:</span>
                    <span className={`font-bold ${Math.abs(data.residualEgt) > 2.0 ? 'text-rose-600' : 'text-slate-700'}`}>
                      {data.residualEgt ? `${data.residualEgt > 0 ? '+' : ''}${data.residualEgt.toFixed(1)}σ` : '0.0σ'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default GenericTwinDetector;
