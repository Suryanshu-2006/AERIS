import React, { useState } from 'react';
import { X, ShieldAlert, Trash2, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';

interface FaultInjectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeFaults: any[];
  onInjectFault?: (faultId: string, severity: number) => void;
  onClearFaults?: () => void;
}

export const FaultInjectorModal: React.FC<FaultInjectorModalProps> = ({
  isOpen,
  onClose,
  activeFaults,
  onInjectFault,
  onClearFaults,
}) => {
  const [selectedFault, setSelectedFault] = useState<string>('OIL_PRESSURE_LOSS');
  const [severity, setSeverity] = useState<number>(0.6);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [injectSuccess, setInjectSuccess] = useState<string | null>(null);

  if (!isOpen) return null;

  const faultCatalog = [
    {
      id: 'OIL_PRESSURE_LOSS',
      name: 'Oil Pressure Loss',
      type: 'MECHANICAL',
      subsystem: 'Lubrication',
      desc: 'Progressive oil seal leak and pump degradation. Affects lubrication, friction, vibration, and thermal load.',
    },
    {
      id: 'COOLING_DEGRADATION_CYL2',
      name: 'Cylinder 2 Cooling Degradation',
      type: 'MECHANICAL',
      subsystem: 'Cooling',
      desc: 'Cooling fin obstruction or baffle failure on Cylinder 2. Causes localized CHT rise.',
    },
    {
      id: 'TURBO_BOOST_DEFICIENCY',
      name: 'Turbo Boost Deficiency',
      type: 'MECHANICAL',
      subsystem: 'Turbo',
      desc: 'Wastegate leak or compressor blade fouling. Causes manifold pressure loss at high altitude.',
    },
    {
      id: 'BEARING_WEAR',
      name: 'Crankshaft Bearing Wear',
      type: 'MECHANICAL',
      subsystem: 'Mechanical',
      desc: 'Mechanical journal bearing wear, elevating high-frequency vibration and oil temperature.',
    },
    {
      id: 'LEAN_MIXTURE_CYL3',
      name: 'Lean Mixture (Cylinder 3)',
      type: 'MECHANICAL',
      subsystem: 'Combustion',
      desc: 'Fuel injector partial restriction leading to lean burn, elevated EGT on CYL 3.',
    },
    {
      id: 'EGT3_BIAS',
      name: 'EGT3 Sensor Bias (+120°C)',
      type: 'SENSOR',
      subsystem: 'Sensors',
      desc: 'Thermocouple electrical bias. Demonstrates sensor fault vs physical engine fault separation.',
    },
    {
      id: 'OIL_PRESSURE_SENSOR_BIAS',
      name: 'Oil Pressure Sensor Bias (-15 psi)',
      type: 'SENSOR',
      subsystem: 'Sensors',
      desc: 'Transducer calibration shift without actual lubrication pressure drop.',
    },
  ];

  const handleInject = async () => {
    setSubmitting(true);
    setInjectSuccess(null);
    try {
      // 1. Call backend API
      await api.injectFault(selectedFault, severity);
      // 2. Invoke reactive state callback for instant UI update
      if (onInjectFault) {
        onInjectFault(selectedFault, severity);
      }
      setInjectSuccess(`Fault ${selectedFault} injected at ${(severity * 100).toFixed(0)}% severity!`);
      setTimeout(() => setInjectSuccess(null), 3000);
    } catch (e) {
      console.error('Inject fault error:', e);
    } finally {
      setSubmitting(false);
    }
  };

  const handleClearAll = async () => {
    setSubmitting(true);
    try {
      // 1. Call backend API
      await api.clearFaults();
      // 2. Invoke reactive state callback
      if (onClearFaults) {
        onClearFaults();
      }
      setInjectSuccess('All active faults cleared successfully.');
      setTimeout(() => setInjectSuccess(null), 2500);
    } catch (e) {
      console.error('Clear faults error:', e);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-2.5">
            <ShieldAlert className="w-5 h-5 text-rose-600" />
            <div>
              <h3 className="font-mono text-sm font-bold text-slate-800 uppercase tracking-wider">
                Fault Injection Matrix &amp; Sensor Isolation Testing
              </h3>
              <p className="text-xs text-slate-500 font-sans">
                Inject deterministic mechanical failure modes or sensor artifacts to evaluate AI detector response
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 overflow-y-auto">
          {/* Success Banner */}
          {injectSuccess && (
            <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-mono flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{injectSuccess}</span>
            </div>
          )}

          {/* Active Faults Banner */}
          {activeFaults && activeFaults.length > 0 && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-between">
              <div>
                <span className="text-xs font-mono font-bold text-rose-800 block">
                  Active Injected Faults ({activeFaults.length})
                </span>
                <span className="text-[11px] font-mono text-rose-600 font-bold">
                  {activeFaults.map((f: any) => f.fault_id || f.id || f).join(', ')}
                </span>
              </div>
              <button
                onClick={handleClearAll}
                disabled={submitting}
                className="flex items-center gap-1.5 px-3 py-1 rounded bg-rose-600 hover:bg-rose-700 active:scale-95 text-white font-mono text-xs font-bold transition-all cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>CLEAR ALL</span>
              </button>
            </div>
          )}

          {/* Fault Selection Grid */}
          <div className="space-y-2">
            <label className="text-xs font-mono font-bold text-slate-700 uppercase tracking-wider">
              Select Fault Pattern to Inject:
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {faultCatalog.map((f) => (
                <div
                  key={f.id}
                  onClick={() => setSelectedFault(f.id)}
                  className={`p-3 rounded-lg border cursor-pointer font-mono transition-all text-xs ${
                    selectedFault === f.id
                      ? 'bg-blue-50 border-blue-500 ring-2 ring-blue-200 shadow-xs'
                      : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-100'
                  }`}
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-bold text-slate-800">{f.name}</span>
                    <span
                      className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                        f.type === 'SENSOR'
                          ? 'bg-purple-100 text-purple-700 border border-purple-200'
                          : 'bg-rose-100 text-rose-700 border border-rose-200'
                      }`}
                    >
                      {f.type}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 line-clamp-2">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Severity Slider */}
          <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200 space-y-2 font-mono text-xs">
            <div className="flex justify-between items-center">
              <span className="text-slate-700 font-bold">Fault Severity Level</span>
              <span className="font-bold text-amber-700">{(severity * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              value={severity}
              onChange={(e) => setSeverity(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>Mild (10%)</span>
              <span>Moderate (50%)</span>
              <span>Critical (100%)</span>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3.5 border-t border-slate-200 bg-slate-50 flex justify-between items-center">
          <button
            onClick={handleClearAll}
            disabled={submitting || (activeFaults?.length ?? 0) === 0}
            className="px-3 py-1.5 rounded bg-slate-200 hover:bg-slate-300 disabled:opacity-40 text-slate-700 font-mono text-xs font-semibold transition-all active:scale-95 cursor-pointer"
          >
            Clear Active Faults
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded bg-slate-200 hover:bg-slate-300 text-slate-700 font-mono text-xs font-medium transition-all active:scale-95 cursor-pointer"
            >
              Close
            </button>
            <button
              onClick={handleInject}
              disabled={submitting}
              className="px-5 py-1.5 rounded bg-rose-600 hover:bg-rose-700 active:scale-95 text-white font-mono font-bold text-xs shadow-xs transition-all cursor-pointer"
            >
              {submitting ? 'INJECTING...' : 'INJECT FAULT NOW'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FaultInjectorModal;
