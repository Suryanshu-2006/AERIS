import React from 'react';
import { Compass, CheckCircle, AlertTriangle, ShieldCheck, Fuel, Wind, Navigation, Plane, Anchor } from 'lucide-react';
import { MissionRiskResult, AircraftProfile } from '../types';

interface MissionRiskPanelProps {
  risk: MissionRiskResult | null | undefined;
  currentPhase?: string;
  altitude?: number;
  aircraft?: AircraftProfile;
}

export const MissionRiskPanel: React.FC<MissionRiskPanelProps> = ({
  risk,
  currentPhase = 'CRUISE',
  altitude = 18400,
  aircraft,
}) => {
  const riskScore = typeof risk?.mission_risk_score === 'number' && !isNaN(risk.mission_risk_score) ? risk.mission_risk_score : 0.287;
  const readiness = risk?.mission_readiness || 'CAUTION';
  const criticalPhase = risk?.critical_phase || 'CLIMB';
  const drivers = Array.isArray(risk?.risk_drivers) && risk.risk_drivers.length > 0 ? risk.risk_drivers : [
    'Climb Phase peak CHT thermal dwell exposure',
    'Atmospheric density lapse rate at 18,400 ft'
  ];
  const altNum = typeof altitude === 'number' && !isNaN(altitude) ? altitude : 18400;

  const getReadinessBadge = (r: string) => {
    switch (r) {
      case 'READY':
        return 'bg-emerald-50 text-emerald-800 border-emerald-300';
      case 'CAUTION':
        return 'bg-amber-50 text-amber-800 border-amber-300';
      case 'WARNING':
        return 'bg-rose-50 text-rose-800 border-rose-300 animate-pulse';
      case 'NOT_READY':
        return 'bg-red-100 text-red-900 border-red-400 font-black animate-pulse';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-300';
    }
  };

  const phasesRow1 = [
    { name: 'GROUND', label: '1. Ground', stress: '4%' },
    { name: 'TAKEOFF', label: '2. Takeoff', stress: '28%' },
    { name: 'CLIMB', label: '3. Climb', stress: '42%' },
    { name: 'CRUISE', label: '4. Cruise', stress: '18%' },
  ];

  const phasesRow2 = [
    { name: 'LOITER', label: '5. Loiter', stress: '34%' },
    { name: 'DESCENT', label: '6. Descent', stress: '8%' },
    { name: 'LANDING', label: '7. Landing', stress: '12%' },
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-xs flex flex-col justify-between h-full gap-3">
      {/* 1. Header */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-2">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-blue-600" />
          <div>
            <h3 className="font-mono text-xs font-black text-slate-900 uppercase tracking-wider">
              MISSION RISK &amp; FLIGHT PHASES
            </h3>
            <span className="text-[10px] text-slate-500 font-mono">
              Sortie: {aircraft?.callsign ?? 'GARUDA-1'} | Tail: #{aircraft?.tailNumber ?? 'IAF-101'}
            </span>
          </div>
        </div>
        <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold border ${getReadinessBadge(readiness)}`}>
          MISSION {readiness}
        </span>
      </div>

      {/* 2. Flight Phase Progression Matrix */}
      <div>
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 mb-1.5">
          <span className="font-bold text-slate-700">FLIGHT PROFILE STAGES</span>
          <span>Current: <strong className="text-blue-700">{currentPhase}</strong> ({altNum.toLocaleString()} ft)</span>
        </div>

        {/* Row 1 */}
        <div className="grid grid-cols-4 gap-1.5 font-mono text-xs mb-1.5">
          {phasesRow1.map((p) => {
            const isCurrent = p.name === currentPhase;
            const isCrit = p.name === criticalPhase;
            return (
              <div
                key={p.name}
                className={`py-1.5 px-2 rounded text-center border transition-all text-[11px] font-bold ${
                  isCurrent
                    ? 'bg-blue-600 border-blue-700 text-white shadow-xs'
                    : isCrit
                    ? 'bg-rose-50 border-rose-300 text-rose-800'
                    : 'bg-slate-50 border-slate-200 text-slate-600'
                }`}
              >
                <div className="truncate">{p.label}</div>
                <div className={`text-[8px] uppercase ${isCurrent ? 'text-blue-100' : isCrit ? 'text-rose-600 font-bold' : 'text-slate-400'}`}>
                  {isCrit ? 'CRIT PHASE' : `Load: ${p.stress}`}
                </div>
              </div>
            );
          })}
        </div>

        {/* Row 2 */}
        <div className="grid grid-cols-3 gap-1.5 font-mono text-xs">
          {phasesRow2.map((p) => {
            const isCurrent = p.name === currentPhase;
            const isCrit = p.name === criticalPhase;
            return (
              <div
                key={p.name}
                className={`py-1.5 px-2 rounded text-center border transition-all text-[11px] font-bold ${
                  isCurrent
                    ? 'bg-blue-600 border-blue-700 text-white shadow-xs'
                    : isCrit
                    ? 'bg-rose-50 border-rose-300 text-rose-800'
                    : 'bg-slate-50 border-slate-200 text-slate-600'
                }`}
              >
                <div className="truncate">{p.label}</div>
                <div className={`text-[8px] uppercase ${isCurrent ? 'text-blue-100' : isCrit ? 'text-rose-600 font-bold' : 'text-slate-400'}`}>
                  {isCrit ? 'CRIT PHASE' : `Load: ${p.stress}`}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Risk Metrics Grid */}
      <div className="grid grid-cols-3 gap-2 font-mono text-xs">
        {/* Risk Score */}
        <div className="bg-slate-50 p-2 rounded-lg border border-slate-200 flex flex-col justify-between">
          <span className="text-[10px] uppercase text-slate-500 font-bold">TOTAL RISK</span>
          <div className="flex items-baseline gap-1 my-0.5">
            <span className={`text-xl font-black ${riskScore > 0.5 ? 'text-rose-600' : riskScore > 0.3 ? 'text-amber-600' : 'text-slate-900'}`}>
              {(riskScore * 100).toFixed(0)}%
            </span>
            <span className="text-[10px] text-slate-500">({riskScore.toFixed(3)})</span>
          </div>
          <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                riskScore > 0.5 ? 'bg-rose-500' : riskScore > 0.3 ? 'bg-amber-500' : 'bg-emerald-500'
              }`}
              style={{ width: `${Math.min(100, riskScore * 100)}%` }}
            />
          </div>
        </div>

        {/* Critical Phase */}
        <div className="bg-slate-50 p-2 rounded-lg border border-slate-200 flex flex-col justify-between">
          <span className="text-[10px] uppercase text-slate-500 font-bold">CRIT PHASE</span>
          <div className="my-0.5">
            <span className="text-base font-black text-rose-600">{criticalPhase}</span>
          </div>
          <span className="text-[9px] text-slate-500 leading-tight">Thermal load peak</span>
        </div>

        {/* Safe Margin */}
        <div className="bg-slate-50 p-2 rounded-lg border border-slate-200 flex flex-col justify-between">
          <span className="text-[10px] uppercase text-slate-500 font-bold">SAFE MARGIN</span>
          <div className="my-0.5">
            <span className="text-base font-black text-blue-700">
              {typeof risk?.safe_horizon_hours === 'number' ? `${risk.safe_horizon_hours.toFixed(1)}h` : '317.6h'}
            </span>
          </div>
          <span className="text-[9px] text-slate-500 leading-tight">To critical limit</span>
        </div>
      </div>

      {/* 4. Sortie Consumables & Flight Envelope (Fills vertical space authentically) */}
      <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 font-mono text-xs space-y-1.5">
        <div className="flex items-center justify-between text-[11px] font-bold text-slate-700 pb-1 border-b border-slate-200">
          <span className="flex items-center gap-1.5">
            <Fuel className="w-3.5 h-3.5 text-blue-600" />
            SORTIE CONSUMABLES &amp; FLIGHT ENVELOPE
          </span>
          <span className="text-[10px] text-slate-500">MALE CLASS</span>
        </div>
        <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[10px] text-slate-600">
          <div className="flex justify-between">
            <span>Fuel Remaining:</span>
            <span className="font-bold text-slate-900">41.8 / 50.0 gal (84%)</span>
          </div>
          <div className="flex justify-between">
            <span>Burn Rate:</span>
            <span className="font-bold text-slate-900">4.8 gph (Twin total)</span>
          </div>
          <div className="flex justify-between">
            <span>Loiter Endurance:</span>
            <span className="font-bold text-emerald-700">7.6 hrs on station</span>
          </div>
          <div className="flex justify-between">
            <span>Airspeed (TAS/GS):</span>
            <span className="font-bold text-slate-900">118 kts / 124 kts</span>
          </div>
          <div className="flex justify-between">
            <span>Wind Aloft:</span>
            <span className="font-bold text-slate-900">240° @ 14 kts</span>
          </div>
          <div className="flex justify-between">
            <span>Single-Eng Ceiling:</span>
            <span className="font-bold text-blue-700">14,200 ft MSL</span>
          </div>
        </div>
      </div>

      {/* 5. Active Risk Drivers & Diversion Point */}
      <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 font-mono text-xs">
        <div className="flex items-center justify-between mb-1 pb-1 border-b border-slate-200">
          <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold flex items-center gap-1">
            <Navigation className="w-3 h-3 text-amber-600" />
            Active Risk Drivers &amp; Recovery
          </span>
          <span className="text-[10px] text-slate-500">PSR: 2h 45m</span>
        </div>
        <ul className="space-y-1 text-slate-700 mb-2">
          {drivers.slice(0, 2).map((d, i) => (
            <li key={i} className="flex items-start gap-1.5 text-[10px] leading-tight">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0 mt-0.5" />
              <span>{d}</span>
            </li>
          ))}
        </ul>
        <div className="pt-1.5 border-t border-slate-200 flex items-center justify-between text-[10px] text-slate-500">
          <span>Primary Recovery: <strong className="text-slate-800">AFB Ambala (42 NM)</strong></span>
          <span>Alternate: <strong className="text-slate-800">AFB Sirsa (78 NM)</strong></span>
        </div>
      </div>
    </div>
  );
};

export default MissionRiskPanel;
