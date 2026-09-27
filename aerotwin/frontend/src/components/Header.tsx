import React, { useState } from 'react';
import { Play, Pause, RotateCcw, ShieldAlert, Plane, Radio, CheckCircle2, ChevronDown } from 'lucide-react';
import { SystemState, AircraftProfile } from '../types';
import { FLEET_AIRCRAFT } from '../services/fleet';
import { api } from '../services/api';

interface HeaderProps {
  state: SystemState | null;
  activeAircraft: AircraftProfile;
  onSelectAircraft: (aircraft: AircraftProfile) => void;
  onStart: () => void;
  onPause: () => void;
  onReset: () => void;
  onSpeed: (speed: number) => void;
  onOpenFaults: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  state,
  activeAircraft,
  onSelectAircraft,
  onStart,
  onPause,
  onReset,
  onSpeed,
  onOpenFaults,
}) => {
  const [selectedSpeed, setSelectedSpeed] = useState<number>(1);
  const [isClearing, setIsClearing] = useState<boolean>(false);

  const isRunning = state?.is_running ?? false;
  const isPaused = state?.is_paused ?? false;
  const activeFaultCount = state?.active_faults?.length ?? 0;
  const simTime = state?.timestamp ? state.timestamp.toFixed(1) : '0.0';

  const handleSpeedChange = (speed: number) => {
    setSelectedSpeed(speed);
    onSpeed(speed);
  };

  const handleQuickClearFaults = async () => {
    setIsClearing(true);
    try {
      await api.clearFaults();
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 sticky top-0 z-40 select-none shadow-xs">
      {/* Brand & Fleet Aircraft Selector */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Brand Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-blue-700 flex items-center justify-center font-mono font-black text-white text-lg shadow-xs shrink-0">
            Æ
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-mono font-black tracking-wider text-base text-slate-900">AERIS</span>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200">
                DRDO SIH26054
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-sans leading-none">
              Aero Piston Twin Digital Twin &amp; Risk Intelligence
            </p>
          </div>
        </div>

        {/* Divider */}
        <div className="hidden md:block h-7 w-[1px] bg-slate-200" />

        {/* Active Aircraft Fleet Switcher */}
        <div className="flex items-center gap-2 bg-slate-50 p-1.5 rounded-lg border border-slate-300">
          <div className="p-1 rounded bg-blue-100 text-blue-700">
            <Plane className="w-4 h-4" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-mono font-bold text-slate-500 uppercase">AIRCRAFT:</span>
              <select
                value={activeAircraft.id}
                onChange={(e) => {
                  const target = FLEET_AIRCRAFT.find((a) => a.id === e.target.value);
                  if (target) onSelectAircraft(target);
                }}
                className="text-xs font-mono font-bold text-slate-900 bg-transparent border-none cursor-pointer focus:outline-none"
              >
                {FLEET_AIRCRAFT.map((ac) => (
                  <option key={ac.id} value={ac.id}>
                    {ac.id}: {ac.model} (Tail #{ac.tailNumber})
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500">
              <span className="text-emerald-700 font-bold flex items-center gap-0.5">
                <Radio className="w-2.5 h-2.5 animate-pulse" />
                {activeAircraft.status}
              </span>
              <span>•</span>
              <span className="truncate max-w-[200px]">{activeAircraft.engineConfig}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Control Buttons & Execution States */}
      <div className="flex flex-wrap items-center gap-2.5">
        {/* Real-Time Live Clock Badge */}
        <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono">
          <span className="relative flex h-2 w-2">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isRunning && !isPaused ? 'bg-emerald-400' : 'bg-amber-400'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                isRunning && !isPaused ? 'bg-emerald-600' : 'bg-amber-500'
              }`}
            />
          </span>
          <span className="font-semibold text-slate-700 text-[11px]">
            {isRunning && !isPaused ? 'TWIN 20Hz' : isPaused ? 'PAUSED' : 'STANDBY'}
          </span>
          <span className="text-slate-300">|</span>
          <span className="text-slate-700 font-bold text-[11px]">T+{simTime}s</span>
        </div>

        {/* Speed selectors */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-mono">
          <span className="text-[10px] text-slate-500 px-1 font-semibold">SPEED:</span>
          {[1, 5, 10, 20].map((s) => (
            <button
              key={s}
              onClick={() => handleSpeedChange(s)}
              className={`px-2 py-0.5 rounded font-bold text-xs transition-all ${
                selectedSpeed === s
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
              }`}
              title={`Simulate at ${s}x Real-Time`}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Play / Pause / Reset Controls */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
          {!isRunning || isPaused ? (
            <button
              onClick={onStart}
              className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white text-xs font-mono font-bold transition-all shadow-xs cursor-pointer"
              title="Run Engine Simulation"
            >
              <Play className="w-3 h-3 fill-current" />
              <span>RUN</span>
            </button>
          ) : (
            <button
              onClick={onPause}
              className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-amber-500 hover:bg-amber-600 active:scale-95 text-white text-xs font-mono font-bold transition-all shadow-xs cursor-pointer"
              title="Pause Simulation"
            >
              <Pause className="w-3 h-3 fill-current" />
              <span>PAUSE</span>
            </button>
          )}

          <button
            onClick={onReset}
            className="p-1 rounded-md text-slate-600 hover:text-slate-900 hover:bg-slate-200 active:scale-95 transition-all cursor-pointer"
            title="Reset Simulation State"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Quick Clear Faults button if faults exist */}
        {activeFaultCount > 0 && (
          <button
            onClick={handleQuickClearFaults}
            disabled={isClearing}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-mono font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 transition-all active:scale-95 cursor-pointer"
            title="Clear all active injected faults"
          >
            <span>CLEAR FAULTS</span>
          </button>
        )}

        {/* Fault Injection Trigger Button */}
        <button
          onClick={onOpenFaults}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold border transition-all active:scale-95 cursor-pointer ${
            activeFaultCount > 0
              ? 'bg-rose-50 border-rose-300 text-rose-700 ring-2 ring-rose-200 animate-pulse'
              : 'bg-white hover:bg-slate-50 border-slate-300 text-slate-700 hover:border-blue-400'
          }`}
          title="Open Fault Injection Matrix"
        >
          <ShieldAlert className={`w-3.5 h-3.5 ${activeFaultCount > 0 ? 'text-rose-600' : 'text-slate-500'}`} />
          <span>INJECT FAULT</span>
          {activeFaultCount > 0 && (
            <span className="px-1.5 py-0.1 rounded-full text-[10px] bg-rose-600 text-white font-black">
              {activeFaultCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
};

export default Header;
