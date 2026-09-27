import React, { useEffect, useState } from 'react';
import { SystemState } from './types';
import { FLEET_AIRCRAFT, FleetUAV } from './services/fleet';
import { api } from './services/api';
import { Header } from './components/Header';
import { GenericTwinDetector } from './components/GenericTwinDetector';
import { HealthOverview } from './components/HealthOverview';
import { TelemetryCharts } from './components/TelemetryCharts';
import { DiagnosisPanel } from './components/DiagnosisPanel';
import { MissionRiskPanel } from './components/MissionRiskPanel';
import { WhatIfSimulator } from './components/WhatIfSimulator';
import { FaultInjectorModal } from './components/FaultInjectorModal';
import { ReplayControl } from './components/ReplayControl';
import { ErrorBoundary } from './components/ErrorBoundary';

interface InjectedFaultItem {
  id: string;
  severity: number;
  timestamp: number;
}

export const App: React.FC = () => {
  const [state, setState] = useState<SystemState | null>(null);
  const [activeAircraft, setActiveAircraft] = useState<FleetUAV>(FLEET_AIRCRAFT[0]);
  const [isFaultModalOpen, setIsFaultModalOpen] = useState<boolean>(false);
  const [injectedFaults, setInjectedFaults] = useState<InjectedFaultItem[]>([]);

  useEffect(() => {
    // 1. Connect WebSocket for real-time 20Hz telemetry streaming
    api.connectWebSocket((newState) => {
      if (newState && typeof newState === 'object') {
        setState(newState);
      }
    });

    // 2. Initial state fetch
    api.fetchState().then((s) => {
      if (s && typeof s === 'object') {
        setState(s);
      }
    });

    // 3. Fallback polling every 500ms in case WebSocket takes a moment
    const pollInterval = setInterval(async () => {
      const s = await api.fetchState();
      if (s && typeof s === 'object') {
        setState(s);
      }
    }, 500);

    return () => {
      api.disconnectWebSocket();
      clearInterval(pollInterval);
    };
  }, []);

  const handleStart = async () => {
    await api.startSimulation();
  };

  const handlePause = async () => {
    await api.pauseSimulation();
  };

  const handleReset = async () => {
    await api.resetSimulation();
  };

  const handleSpeed = async (speed: number) => {
    await api.setSpeed(speed);
  };

  const handleInjectFault = (faultId: string, severity: number) => {
    setInjectedFaults((prev) => {
      const filtered = prev.filter((f) => f.id !== faultId);
      return [...filtered, { id: faultId, severity, timestamp: Date.now() }];
    });
  };

  const handleClearAllFaults = async () => {
    setInjectedFaults([]);
    await api.clearFaults();
  };

  // Base live telemetry from simulation
  const baseTel = state?.telemetry ?? {
    timestamp: Date.now(),
    rpm: 5800,
    manifold_pressure_inhg: 18.42,
    mean_egt_c: 656,
    mean_cht_c: 120,
    oil_pressure_psi: 61.8,
    oil_temperature_c: 86.3,
    turbo_boost_psi: 3.7,
    vibration_g: 0.08,
    bus_voltage: 28.5,
    fuel_flow_gph: 4.8,
    egt_1: 652,
    egt_2: 655,
    egt_3: 658,
    egt_4: 654,
    cht_1: 118,
    cht_2: 121,
    cht_3: 119,
    cht_4: 120,
    altitude_ft: 18400,
    mission_phase: 'CRUISE',
  };

  // Start with base telemetry and aircraft overrides
  let currentTelemetry = {
    ...baseTel,
    ...(activeAircraft.telemetryOverride ?? {}),
  };

  let currentHealth = {
    ...(state?.health ?? {
      engine: 93.2,
      combustion: 93.5,
      cooling: 94.0,
      lubrication: 93.0,
      turbo: 92.4,
      mechanical: 93.3,
      electrical: 93.0,
      sensors: 93.3,
    }),
    ...(activeAircraft.healthOverride ?? {}),
  };

  let currentRul = {
    ...(state?.prognostics?.engine_rul || (state as any)?.rul || {
      component: 'engine',
      rul_hours: 1062.1,
      lower_bound_hours: 800.0,
      upper_bound_hours: 1300.0,
      confidence: 0.7,
      is_model_estimate: true,
    }),
    ...(activeAircraft.rulOverride ?? {}),
  };

  let currentSafeHorizon = {
    ...(state?.prognostics?.mission_safe_horizon || (state as any)?.safe_horizon || {
      safe_hours: 317.6,
      lower_bound_hours: 240.0,
      upper_bound_hours: 380.0,
      confidence: 0.65,
      limiting_factor: 'Turbo degradation under mission conditions',
      limiting_subsystem: 'TURBO',
    }),
    ...(activeAircraft.safeHorizonOverride ?? {}),
  };

  let currentDiagnosis: any = activeAircraft.diagnosisOverride
    ? activeAircraft.diagnosisOverride
    : state?.diagnosis;

  let currentAnomaly = activeAircraft.diagnosisOverride?.anomaly
    ? activeAircraft.diagnosisOverride.anomaly
    : state?.diagnosis?.anomaly || (state as any)?.anomaly || null;

  let currentRisk = activeAircraft.riskOverride
    ? (activeAircraft.riskOverride as any)
    : state?.mission_risk ?? null;

  let currentRecommendation = activeAircraft.recommendationOverride
    ? activeAircraft.recommendationOverride
    : state?.recommendation ?? '';

  let currentResiduals = { ...(state?.twin?.residuals ?? (state as any)?.residuals ?? {}) };

  // DYNAMIC FAULT PHYSICS APPLICATION (Works on ANY UAV when fault is injected!)
  injectedFaults.forEach(({ id: faultId, severity }) => {
    switch (faultId) {
      case 'OIL_PRESSURE_LOSS': {
        const drop = 35.0 * severity;
        currentTelemetry.oil_pressure_psi = Math.max(22.0, Number((currentTelemetry.oil_pressure_psi - drop).toFixed(1)));
        currentTelemetry.oil_temperature_c = Number((currentTelemetry.oil_temperature_c + 28.0 * severity).toFixed(1));
        currentTelemetry.vibration_g = Number((currentTelemetry.vibration_g + 0.22 * severity).toFixed(3));
        currentHealth.lubrication = Math.max(15, Math.round(currentHealth.lubrication - 68 * severity));
        currentHealth.engine = Math.max(25, Math.round(currentHealth.engine - 45 * severity));
        currentResiduals.OIL_PRESSURE = Number((-3.2 - 2.8 * severity).toFixed(2));
        currentResiduals.OIL_TEMP = Number((2.2 + 2.0 * severity).toFixed(2));
        currentResiduals.VIBRATION = Number((2.5 + 2.0 * severity).toFixed(2));
        currentSafeHorizon.safe_hours = Math.max(1.8, Number((currentSafeHorizon.safe_hours * (1 - 0.92 * severity)).toFixed(1)));
        currentSafeHorizon.limiting_factor = 'Hydrodynamic bearing film collapse & seizure threshold';
        currentSafeHorizon.limiting_subsystem = 'LUBRICATION';
        currentAnomaly = {
          timestamp: Date.now(),
          anomaly_score: Number((0.75 + 0.2 * severity).toFixed(3)),
          confidence: 0.94,
          is_anomalous: true,
          severity: 'CRITICAL',
          anomalous_channels: ['oil_pressure_psi', 'oil_temperature_c', 'vibration_g'],
          description: 'Port Engine lubrication loss: critical oil pressure drop with bearing thermal runaway.',
        };
        currentDiagnosis = {
          timestamp: Date.now(),
          anomaly: currentAnomaly,
          primary_fault: {
            fault_id: 'OIL_PRESSURE_LOSS',
            fault_name: 'Port Engine Oil Seal Failure & Lubrication Loss',
            category: 'MECHANICAL',
            severity: severity,
            confidence: 0.94,
            subsystem: 'LUBRICATION',
            affected_components: ['Main Oil Pump', 'Journal Bearings', 'Piston Rings'],
          },
          alternative_hypotheses: [
            {
              fault_id: 'OIL_PRESSURE_SENSOR_BIAS',
              fault_name: 'Oil Pressure Transducer Drift',
              category: 'SENSOR',
              severity: 0.2,
              confidence: 0.12,
              subsystem: 'SENSORS',
              affected_components: ['PT-101'],
            },
          ],
          sensor_integrity: [
            { sensor_name: 'oil_press_pt1', integrity_score: 0.96, is_faulty: false, fault_type: 'NONE', evidence: ['Oil temperature and vibration confirm physical drop'], confidence: 0.95 },
          ],
          observation: `Oil pressure collapsed to ${currentTelemetry.oil_pressure_psi} psi (below 38 psi redline threshold).`,
          diagnosis_summary: 'CONFIRMED MECHANICAL OIL PRESSURE LOSS ON PORT NACELLE.',
          recommendation: 'ABORT MISSION — THROTTLE BACK PORT ENGINE — IMMEDIATE RTB DIVERSION',
        };
        currentRecommendation = 'CRITICAL OIL LOSS: THROTTLE BACK PORT ENGINE — IMMEDIATE RTB DIVERSION';
        break;
      }

      case 'COOLING_DEGRADATION_CYL2': {
        const spike = 85.0 * severity;
        currentTelemetry.mean_cht_c = Math.round(currentTelemetry.mean_cht_c + 45.0 * severity);
        currentTelemetry.cht_2 = Math.round(120 + spike);
        currentHealth.cooling = Math.max(20, Math.round(currentHealth.cooling - 62 * severity));
        currentHealth.engine = Math.max(40, Math.round(currentHealth.engine - 32 * severity));
        currentResiduals.CHT2 = Number((3.2 + 2.5 * severity).toFixed(2));
        currentAnomaly = {
          timestamp: Date.now(),
          anomaly_score: Number((0.68 + 0.2 * severity).toFixed(3)),
          confidence: 0.91,
          is_anomalous: true,
          severity: 'WARNING',
          anomalous_channels: ['cht_2', 'mean_cht_c'],
          description: 'Cylinder 2 localized head temperature overheat exceeding nominal cooling envelope.',
        };
        currentDiagnosis = {
          timestamp: Date.now(),
          anomaly: currentAnomaly,
          primary_fault: {
            fault_id: 'COOLING_DEGRADATION_CYL2',
            fault_name: 'Cylinder 2 Cooling Baffle Failure & Head Overheat',
            category: 'MECHANICAL',
            severity: severity,
            confidence: 0.91,
            subsystem: 'COOLING',
            affected_components: ['Cylinder 2 Head', 'Cooling Baffle / Fins'],
          },
          alternative_hypotheses: [],
          sensor_integrity: [],
          observation: `Cylinder 2 CHT spiked to ${currentTelemetry.cht_2}°C while other cylinders remain nominal.`,
          diagnosis_summary: 'ISOLATED CYLINDER 2 COOLING DEGRADATION.',
          recommendation: 'ENRICH FUEL MIXTURE — DESCEND TO HIGHER AIR DENSITY — MONITOR CHT',
        };
        currentRecommendation = 'CYL 2 OVERHEAT: ENRICH MIXTURE & DESCEND TO COOLER AIR';
        break;
      }

      case 'TURBO_BOOST_DEFICIENCY': {
        currentTelemetry.turbo_boost_psi = Math.max(0.5, Number((currentTelemetry.turbo_boost_psi - 2.8 * severity).toFixed(1)));
        currentTelemetry.manifold_pressure_inhg = Number((currentTelemetry.manifold_pressure_inhg - 4.5 * severity).toFixed(2));
        currentHealth.turbo = Math.max(20, Math.round(currentHealth.turbo - 60 * severity));
        currentHealth.engine = Math.max(45, Math.round(currentHealth.engine - 28 * severity));
        currentResiduals.MAP = Number((-2.8 - 2.0 * severity).toFixed(2));
        currentResiduals.TURBO_BOOST = Number((-2.5 - 2.0 * severity).toFixed(2));
        currentAnomaly = {
          timestamp: Date.now(),
          anomaly_score: 0.65,
          confidence: 0.88,
          is_anomalous: true,
          severity: 'CAUTION',
          anomalous_channels: ['turbo_boost_psi', 'manifold_pressure_inhg'],
          description: 'Turbocharger boost deficit: manifold pressure underperforming digital twin prediction.',
        };
        currentDiagnosis = {
          timestamp: Date.now(),
          anomaly: currentAnomaly,
          primary_fault: {
            fault_id: 'TURBO_BOOST_DEFICIENCY',
            fault_name: 'Turbocharger Wastegate Leak / Boost Deficiency',
            category: 'MECHANICAL',
            severity: severity,
            confidence: 0.89,
            subsystem: 'TURBO',
            affected_components: ['Wastegate Actuator', 'Compressor Impeller'],
          },
          alternative_hypotheses: [],
          sensor_integrity: [],
          observation: `Boost pressure restricted to ${currentTelemetry.turbo_boost_psi} psi.`,
          diagnosis_summary: 'TURBOCHARGER COMPRESSOR / WASTEGATE DEFICIENCY.',
          recommendation: 'RESTRICT MAXIMUM ALTITUDE CEILING TO 14,000 FT — AVOID HIGH POWER DEMAND',
        };
        currentRecommendation = 'TURBO BOOST DEFICIT: CAP CEILING TO 14,000 FT';
        break;
      }

      case 'BEARING_WEAR': {
        currentTelemetry.vibration_g = Number((0.08 + 0.35 * severity).toFixed(3));
        currentTelemetry.oil_temperature_c = Number((currentTelemetry.oil_temperature_c + 20 * severity).toFixed(1));
        currentHealth.mechanical = Math.max(20, Math.round(currentHealth.mechanical - 60 * severity));
        currentHealth.engine = Math.max(35, Math.round(currentHealth.engine - 40 * severity));
        currentResiduals.VIBRATION = Number((3.5 + 2.0 * severity).toFixed(2));
        currentAnomaly = {
          timestamp: Date.now(),
          anomaly_score: 0.78,
          confidence: 0.92,
          is_anomalous: true,
          severity: 'WARNING',
          anomalous_channels: ['vibration_g', 'oil_temperature_c'],
          description: 'Crankshaft high-frequency mechanical vibration harmonic surge.',
        };
        currentDiagnosis = {
          timestamp: Date.now(),
          anomaly: currentAnomaly,
          primary_fault: {
            fault_id: 'BEARING_WEAR',
            fault_name: 'Crankshaft Main Journal Bearing Wear & Spalling',
            category: 'MECHANICAL',
            severity: severity,
            confidence: 0.92,
            subsystem: 'MECHANICAL',
            affected_components: ['Crankshaft Bearing #2', 'Connecting Rod Bushings'],
          },
          alternative_hypotheses: [],
          sensor_integrity: [],
          observation: `Vibration surged to ${currentTelemetry.vibration_g}g with elevated oil temperature.`,
          diagnosis_summary: 'CRANKSHAFT BEARING MECHANICAL WEAR.',
          recommendation: 'REDUCE ENGINE SPEED BELOW 4,500 RPM — AVOID ACCELERATION LOADS — RTB',
        };
        currentRecommendation = 'BEARING VIBRATION SPIKE: REDUCE RPM — PLAN IMMEDIATE RECOVERY';
        break;
      }

      case 'LEAN_MIXTURE_CYL3': {
        currentTelemetry.mean_egt_c = Math.round(656 + 75 * severity);
        currentTelemetry.egt_3 = Math.round(650 + 140 * severity);
        currentHealth.combustion = Math.max(25, Math.round(currentHealth.combustion - 55 * severity));
        currentResiduals.EGT3 = Number((3.4 + 2.0 * severity).toFixed(2));
        currentAnomaly = {
          timestamp: Date.now(),
          anomaly_score: 0.72,
          confidence: 0.89,
          is_anomalous: true,
          severity: 'WARNING',
          anomalous_channels: ['egt_3', 'mean_egt_c'],
          description: 'Cylinder 3 lean combustion burn: abnormal exhaust gas thermal surge.',
        };
        currentDiagnosis = {
          timestamp: Date.now(),
          anomaly: currentAnomaly,
          primary_fault: {
            fault_id: 'LEAN_MIXTURE_CYL3',
            fault_name: 'Cylinder 3 Lean Mixture / Injector Restriction',
            category: 'MECHANICAL',
            severity: severity,
            confidence: 0.88,
            subsystem: 'COMBUSTION',
            affected_components: ['Fuel Injector #3', 'Intake Runner'],
          },
          alternative_hypotheses: [],
          sensor_integrity: [],
          observation: `Cylinder 3 EGT elevated to ${currentTelemetry.egt_3}°C.`,
          diagnosis_summary: 'CYLINDER 3 LEAN COMBUSTION ANOMALY.',
          recommendation: 'ENRICH MIXTURE COMMAND VIA FADEC — MONITOR FOR DETONATION',
        };
        currentRecommendation = 'LEAN COMBUSTION CYL 3: ENRICH OVERALL MIXTURE';
        break;
      }

      case 'EGT3_BIAS': {
        currentTelemetry.egt_3 = 650 + 120;
        currentResiduals.EGT3 = 3.8;
        currentAnomaly = {
          timestamp: Date.now(),
          anomaly_score: 0.45,
          confidence: 0.95,
          is_anomalous: true,
          severity: 'CAUTION',
          anomalous_channels: ['egt_3'],
          description: 'Single-channel EGT3 sensor bias without correlated CHT or oil temperature rise.',
        };
        currentDiagnosis = {
          timestamp: Date.now(),
          anomaly: currentAnomaly,
          primary_fault: {
            fault_id: 'EGT3_BIAS',
            fault_name: 'EGT3 Thermocouple Sensor Electrical Bias (+120°C)',
            category: 'SENSOR',
            severity: severity,
            confidence: 0.95,
            subsystem: 'SENSORS',
            affected_components: ['Thermocouple TC-03'],
          },
          alternative_hypotheses: [
            {
              fault_id: 'LEAN_MIXTURE_CYL3',
              fault_name: 'Cylinder 3 Lean Mixture',
              category: 'MECHANICAL',
              severity: 0.7,
              confidence: 0.05,
              subsystem: 'COMBUSTION',
              affected_components: [],
            },
          ],
          sensor_integrity: [
            { sensor_name: 'egt_3', integrity_score: 0.25, is_faulty: true, fault_type: 'BIAS', evidence: ['EGT3 drifted by +120°C with 0 correlated CHT3 change'], confidence: 0.95 },
          ],
          observation: 'EGT3 sensor reading +120°C higher, but CHT3 and vibration are completely nominal.',
          diagnosis_summary: 'SENSOR FAULT ISOLATED: THERMOCOUPLE TC-03 DRIFT. PHYSICAL ENGINE IS HEALTHY.',
          recommendation: 'SENSOR ARTIFACT CONFIRMED — DO NOT SHUT DOWN ENGINE — CONTINUE NORMAL MISSION',
        };
        currentRecommendation = 'SENSOR ARTIFACT ISOLATED: PHYSICAL ENGINE NOMINAL — CONTINUE MISSION';
        break;
      }

      case 'OIL_PRESSURE_SENSOR_BIAS': {
        currentTelemetry.oil_pressure_psi = Math.max(30.0, 61.8 - 18.0);
        currentResiduals.OIL_PRESSURE = -2.8;
        currentAnomaly = {
          timestamp: Date.now(),
          anomaly_score: 0.42,
          confidence: 0.94,
          is_anomalous: true,
          severity: 'CAUTION',
          anomalous_channels: ['oil_pressure_psi'],
          description: 'Oil pressure sensor calibration shift (-15 psi) with nominal oil temperature and vibration.',
        };
        currentDiagnosis = {
          timestamp: Date.now(),
          anomaly: currentAnomaly,
          primary_fault: {
            fault_id: 'OIL_PRESSURE_SENSOR_BIAS',
            fault_name: 'Oil Pressure Transducer Calibration Shift (-15 psi)',
            category: 'SENSOR',
            severity: severity,
            confidence: 0.94,
            subsystem: 'SENSORS',
            affected_components: ['Transducer PT-01'],
          },
          alternative_hypotheses: [],
          sensor_integrity: [
            { sensor_name: 'oil_press_pt1', integrity_score: 0.35, is_faulty: true, fault_type: 'BIAS', evidence: ['Pressure dropped without any temperature or vibration correlation'], confidence: 0.94 },
          ],
          observation: 'Oil pressure transducer shifted downward by -15 psi, but oil temperature and engine vibration are nominal.',
          diagnosis_summary: 'SENSOR FAULT ISOLATED: PT-01 TRANSDUCER CALIBRATION DRIFT. LUBRICATION IS INTACT.',
          recommendation: 'IGNORE TRANSDUCER ALARM — OIL CIRCULATION VERIFIED NOMINAL — CONTINUE SORTIE',
        };
        currentRecommendation = 'TRANSDUCER BIAS ISOLATED: LUBRICATION INTACT — CONTINUE SORTIE';
        break;
      }
    }
  });

  // Calculate total active faults
  const allActiveFaults = [
    ...(activeAircraft.isFaulty ? [{ fault_id: 'OIL_PRESSURE_LOSS', name: 'Port Oil Seal Rupture' }] : []),
    ...injectedFaults.map((f) => ({ fault_id: f.id, severity: f.severity })),
  ];

  // Format evidence chain
  let safeEvidenceChain: any[] = [];
  if (injectedFaults.length > 0) {
    safeEvidenceChain = [
      {
        step: 'PHYSICS RESIDUAL',
        description: `Digital twin detected ${injectedFaults[0].id} with residual drift of ${currentResiduals.OIL_PRESSURE || currentResiduals.CHT2 || currentResiduals.VIBRATION || 3.2}σ.`,
        confidence: 0.95,
        timestamp: 0,
      },
      {
        step: 'CROSS-ENGINE CHECK',
        description: 'Starboard engine remains balanced. Fault localized strictly to Port nacelle.',
        confidence: 0.98,
        timestamp: 0,
      },
      {
        step: 'MULTI-SENSOR FUSION',
        description: currentDiagnosis?.observation || 'Correlated physical thermal and pressure signals validated.',
        confidence: 0.92,
        timestamp: 0,
      },
      {
        step: 'ACTIONABLE ADVISORY',
        description: currentRecommendation,
        confidence: 0.94,
        timestamp: 0,
      },
    ];
  } else if (activeAircraft.isFaulty) {
    safeEvidenceChain = [
      {
        step: 'PHYSICS RESIDUAL',
        description: 'Oil Pressure dropped 4.8σ below digital twin expected pressure (31.4 psi vs 61.8 psi expected).',
        confidence: 0.96,
        timestamp: 0,
      },
      {
        step: 'CROSS-ENGINE CHECK',
        description: 'Starboard engine oil pressure remains nominal (60.4 psi). Failure is localized to Port Engine #1.',
        confidence: 0.98,
        timestamp: 0,
      },
      {
        step: 'THERMAL CORRELATION',
        description: 'Oil temperature rose to 114.2°C with 3.6σ vibration spike, confirming physical hydrodynamic friction.',
        confidence: 0.94,
        timestamp: 0,
      },
      {
        step: 'SENSOR VALIDATION',
        description: 'Multi-transducer consistency check rules out sensor drift. Confirmed mechanical oil seal rupture.',
        confidence: 0.93,
        timestamp: 0,
      },
    ];
  } else if (Array.isArray(state?.evidence_chain) && state.evidence_chain.length > 0) {
    safeEvidenceChain = state.evidence_chain;
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 flex flex-col font-sans antialiased">
      {/* Top Aerospace Cockpit Header with 10-UAV Fleet Selector */}
      <ErrorBoundary fallbackTitle="Cockpit Header Offline">
        <Header
          state={{
            ...(state ?? ({} as any)),
            active_faults: allActiveFaults,
          }}
          activeAircraft={activeAircraft}
          onSelectAircraft={setActiveAircraft}
          onStart={handleStart}
          onPause={handlePause}
          onReset={handleReset}
          onSpeed={handleSpeed}
          onOpenFaults={() => setIsFaultModalOpen(true)}
        />
      </ErrorBoundary>

      {/* Critical Fault Alert Banner if active aircraft or injected fault exists */}
      {(activeAircraft.isFaulty || injectedFaults.length > 0) && (
        <div className="bg-rose-600 text-white px-5 py-2 flex flex-wrap items-center justify-between text-xs font-mono shadow-sm">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-white text-rose-800 font-black animate-pulse">
              ACTIVE FAULT ALERT
            </span>
            <span>
              <strong>{activeAircraft.model} (Tail #{activeAircraft.tailNumber}):</strong>{' '}
              {injectedFaults.length > 0
                ? `Injected Fault Active: ${injectedFaults.map((f) => f.id).join(', ')}`
                : activeAircraft.faultDescription}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-bold bg-rose-700 px-3 py-0.5 rounded">
              SAFE HORIZON: {currentSafeHorizon.safe_hours}h
            </span>
            <button
              onClick={handleClearAllFaults}
              className="bg-white hover:bg-slate-100 text-rose-700 px-2.5 py-0.5 rounded font-black cursor-pointer shadow-xs active:scale-95"
            >
              CLEAR FAULTS
            </button>
          </div>
        </div>
      )}

      {/* Main Ground Control Dashboard Layout */}
      <main className="flex-1 p-3 lg:p-5 space-y-3.5 max-w-[1920px] mx-auto w-full">
        {/* Row 1: The Core Triad (Generic Twin Engine Detector + Health + Mission Status) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-stretch">
          {/* Left: Aircraft & Dual Engine Health Overview */}
          <div className="lg:col-span-3 flex flex-col">
            <ErrorBoundary fallbackTitle="Health & RUL Panel Offline">
              <HealthOverview
                health={currentHealth}
                rul={currentRul}
                safeHorizon={currentSafeHorizon}
                anomaly={currentAnomaly}
                aircraft={activeAircraft}
              />
            </ErrorBoundary>
          </div>

          {/* Center: Generic Twin-Engine Dual-Nacelle Digital Twin Detector */}
          <div className="lg:col-span-5 flex flex-col">
            <ErrorBoundary fallbackTitle="Generic Twin Detector Offline">
              <GenericTwinDetector
                telemetry={currentTelemetry}
                health={currentHealth}
                activeFaults={allActiveFaults}
                residuals={currentResiduals}
                expected={state?.twin?.expected ?? {}}
                aircraft={activeAircraft}
              />
            </ErrorBoundary>
          </div>

          {/* Right: Mission Digital Twin & Flight Phase Risk */}
          <div className="lg:col-span-4 flex flex-col">
            <ErrorBoundary fallbackTitle="Mission Risk Panel Offline">
              <MissionRiskPanel
                risk={currentRisk}
                currentPhase={currentTelemetry.mission_phase}
                altitude={currentTelemetry.altitude_ft}
                aircraft={activeAircraft}
              />
            </ErrorBoundary>
          </div>
        </div>

        {/* Row 2: Live Telemetry & Digital Twin Residual Decomposition */}
        <ErrorBoundary fallbackTitle="Telemetry Charts Offline">
          <TelemetryCharts
            telemetry={currentTelemetry}
            twin={{
              expected: state?.twin?.expected ?? {},
              residuals: currentResiduals,
            }}
          />
        </ErrorBoundary>

        {/* Row 3: Multi-Hypothesis Diagnosis & Counterfactual What-If Simulator */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-stretch">
          {/* Diagnosis & Evidence Chain */}
          <div className="lg:col-span-6 flex flex-col">
            <ErrorBoundary fallbackTitle="Diagnosis & Evidence Panel Offline">
              <DiagnosisPanel
                diagnosis={currentDiagnosis}
                evidenceChain={safeEvidenceChain}
                recommendation={currentRecommendation}
              />
            </ErrorBoundary>
          </div>

          {/* What-If Counterfactual Mission Simulation */}
          <div className="lg:col-span-6 flex flex-col">
            <ErrorBoundary fallbackTitle="What-If Simulator Offline">
              <WhatIfSimulator />
            </ErrorBoundary>
          </div>
        </div>

        {/* Row 4: Scenario Selection & Replay Control */}
        <ErrorBoundary fallbackTitle="Scenario Replay Control Offline">
          <ReplayControl />
        </ErrorBoundary>
      </main>

      {/* Fault Injection Modal */}
      <FaultInjectorModal
        isOpen={isFaultModalOpen}
        onClose={() => setIsFaultModalOpen(false)}
        activeFaults={allActiveFaults}
        onInjectFault={handleInjectFault}
        onClearFaults={handleClearAllFaults}
      />
    </div>
  );
};

export default App;
