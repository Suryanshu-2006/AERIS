import React, { useState } from 'react';
import { Film, CheckCircle2, PlayCircle } from 'lucide-react';
import { api } from '../services/api';

interface ReplayControlProps {
  onScenarioLoaded?: (id: string) => void;
}

export const ReplayControl: React.FC<ReplayControlProps> = ({ onScenarioLoaded }) => {
  const [selectedScenario, setSelectedScenario] = useState<string>('SCENARIO_01');
  const [loading, setLoading] = useState<boolean>(false);

  const scenarios = [
    { id: 'SCENARIO_01', short: '01: Nominal Cruise', name: '01: Healthy Cruise', desc: 'Nominal surveillance baseline' },
    { id: 'SCENARIO_02', short: '02: Oil Pressure Loss', name: '02: Oil Pressure Loss', desc: 'Progressive lubrication seal leakage' },
    { id: 'SCENARIO_03', short: '03: Turbo Deficiency', name: '03: Turbo Deficiency', desc: 'Turbocharger boost deficit at altitude' },
    { id: 'SCENARIO_04', short: '04: CHT Overheat', name: '04: Cylinder 2 Cooling Degradation', desc: 'Cooling fin obstruction CHT rise' },
    { id: 'SCENARIO_05', short: '05: Bearing Wear', name: '05: Crankshaft Bearing Wear', desc: 'Bearing wear & high-vibration profile' },
    { id: 'SCENARIO_06', short: '06: Sensor Bias', name: '06: EGT3 Sensor Fault', desc: 'Isolated thermocouple bias (sensor isolation test)' },
    { id: 'SCENARIO_07', short: '07: Multi-Fault', name: '07: Combined Sensor + Engine Anomaly', desc: 'Dual-mode simultaneous degradation' },
    { id: 'SCENARIO_08', short: '08: Unknown Anomaly', name: '08: Unknown Anomaly', desc: 'Low-severity non-cataloged anomaly' },
    { id: 'SCENARIO_09', short: '09: High-Altitude Stress', name: '09: High-Altitude Mission', desc: '28,000 ft operational ceiling stress' },
    { id: 'SCENARIO_10', short: '10: Long Loiter Wear', name: '10: Long Loiter Mission', desc: 'Extended 3-hour surveillance wear accumulation' },
  ];

  const handleSelectScenario = async (scId: string) => {
    if (!scId || loading) return;
    setLoading(true);
    setSelectedScenario(scId);
    try {
      await api.loadScenario(scId);
      if (onScenarioLoaded) onScenarioLoaded(scId);
    } catch (e) {
      console.error('Failed to load scenario:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-2.5">
        <div className="flex items-center gap-2">
          <Film className="w-4 h-4 text-blue-600" />
          <div>
            <span className="font-mono text-xs font-bold text-slate-800 uppercase tracking-wider">
              Validation Scenario Selector &amp; Mission Replay
            </span>
            <p className="text-xs text-slate-500 font-sans">
              10 deterministic validation test benches for SIH benchmark verification
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={selectedScenario}
            onChange={(e) => handleSelectScenario(e.target.value)}
            disabled={loading}
            className="bg-slate-50 border border-slate-300 text-slate-800 text-xs font-mono rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-medium"
          >
            {scenarios.map((sc) => (
              <option key={sc.id} value={sc.id}>
                {sc.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Quick Click Scenario Buttons */}
      <div className="flex flex-wrap gap-1.5">
        {scenarios.map((sc) => {
          const isSelected = selectedScenario === sc.id;
          return (
            <button
              key={sc.id}
              onClick={() => handleSelectScenario(sc.id)}
              disabled={loading}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all active:scale-95 ${
                isSelected
                  ? 'bg-blue-600 text-white font-bold shadow-xs'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200'
              }`}
              title={sc.desc}
            >
              {sc.short}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default ReplayControl;
