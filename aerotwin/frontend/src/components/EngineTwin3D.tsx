import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { HealthScores, TelemetryData } from '../types';

interface EngineTwin3DProps {
  telemetry: TelemetryData | null;
  health: HealthScores | null;
  activeFaults: any[];
}

export const EngineTwin3D: React.FC<EngineTwin3DProps> = ({ telemetry, health, activeFaults }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [selectedPart, setSelectedPart] = useState<string>('Overview: All Subsystems Nominal');

  // References to 3D meshes for status coloring
  const meshMapRef = useRef<{ [key: string]: THREE.Mesh | THREE.Group }>({});
  const propGroupRef = useRef<THREE.Group | null>(null);

  useEffect(() => {
    if (!mountRef.current) return;
    const container = mountRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x070b13);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(4.5, 3.2, 5.0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    // 2. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x38bdf8, 2.0);
    dirLight1.position.set(5, 10, 7);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xf59e0b, 0.6);
    dirLight2.position.set(-5, -2, -5);
    scene.add(dirLight2);

    // Grid Floor
    const gridHelper = new THREE.GridHelper(10, 20, 0x1e293b, 0x0f172a);
    gridHelper.position.y = -1.2;
    scene.add(gridHelper);

    // 3. Engine Assembly (Rotax 914 class 4-cylinder boxer)
    const engineGroup = new THREE.Group();
    scene.add(engineGroup);

    // Crankcase
    const crankcaseGeo = new THREE.BoxGeometry(1.6, 1.0, 1.8);
    const crankcaseMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      roughness: 0.4,
      metalness: 0.7,
    });
    const crankcase = new THREE.Mesh(crankcaseGeo, crankcaseMat);
    engineGroup.add(crankcase);
    meshMapRef.current['crankcase'] = crankcase;

    // 4 Cylinders (opposed boxer configuration)
    const cylPositions = [
      { id: 1, pos: [-1.4, 0.2, 0.5] },
      { id: 2, pos: [1.4, 0.2, 0.5] },
      { id: 3, pos: [-1.4, 0.2, -0.5] },
      { id: 4, pos: [1.4, 0.2, -0.5] },
    ];

    cylPositions.forEach((cyl) => {
      const cylGroup = new THREE.Group();
      cylGroup.position.set(cyl.pos[0], cyl.pos[1], cyl.pos[2]);

      // Cylinder barrel
      const barrelGeo = new THREE.CylinderGeometry(0.32, 0.32, 0.9, 24);
      barrelGeo.rotateZ(Math.PI / 2);
      const barrelMat = new THREE.MeshStandardMaterial({
        color: 0x475569,
        roughness: 0.3,
        metalness: 0.8,
      });
      const barrel = new THREE.Mesh(barrelGeo, barrelMat);
      cylGroup.add(barrel);

      // Cooling fins
      for (let f = -0.3; f <= 0.3; f += 0.12) {
        const finGeo = new THREE.CylinderGeometry(0.38, 0.38, 0.02, 24);
        finGeo.rotateZ(Math.PI / 2);
        const finMat = new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.9 });
        const fin = new THREE.Mesh(finGeo, finMat);
        fin.position.x = f;
        cylGroup.add(fin);
      }

      // Cylinder Head
      const headGeo = new THREE.BoxGeometry(0.25, 0.7, 0.7);
      const headMat = new THREE.MeshStandardMaterial({
        color: 0x0284c7, // default cyan
        roughness: 0.2,
        metalness: 0.8,
      });
      const head = new THREE.Mesh(headGeo, headMat);
      head.position.x = cyl.pos[0] > 0 ? 0.5 : -0.5;
      cylGroup.add(head);

      engineGroup.add(cylGroup);
      meshMapRef.current[`cyl_${cyl.id}`] = head;
    });

    // Turbocharger (aft side)
    const turboGroup = new THREE.Group();
    turboGroup.position.set(0, 0.3, -1.4);

    const turbineGeo = new THREE.TorusGeometry(0.35, 0.15, 16, 32);
    const turbineMat = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.3, metalness: 0.9 });
    const turbine = new THREE.Mesh(turbineGeo, turbineMat);
    turboGroup.add(turbine);

    const wastegateGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.4, 16);
    const wastegateMat = new THREE.MeshStandardMaterial({ color: 0x71717a, metalness: 0.8 });
    const wastegate = new THREE.Mesh(wastegateGeo, wastegateMat);
    wastegate.position.set(0.3, 0.2, 0);
    turboGroup.add(wastegate);

    engineGroup.add(turboGroup);
    meshMapRef.current['turbo'] = turbine;

    // Oil Sump (bottom)
    const sumpGeo = new THREE.BoxGeometry(1.2, 0.35, 1.4);
    const sumpMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.6, metalness: 0.5 });
    const sump = new THREE.Mesh(sumpGeo, sumpMat);
    sump.position.y = -0.65;
    engineGroup.add(sump);
    meshMapRef.current['oil_sump'] = sump;

    // Propeller / Shaft (front)
    const propGroup = new THREE.Group();
    propGroup.position.set(0, 0, 1.05);

    const spinnerGeo = new THREE.ConeGeometry(0.25, 0.5, 24);
    spinnerGeo.rotateX(Math.PI / 2);
    const spinnerMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.1, metalness: 0.9 });
    const spinner = new THREE.Mesh(spinnerGeo, spinnerMat);
    propGroup.add(spinner);

    // Propeller Blades (2-blade composite)
    const bladeGeo = new THREE.BoxGeometry(2.4, 0.12, 0.02);
    const bladeMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.4 });
    const blade = new THREE.Mesh(bladeGeo, bladeMat);
    propGroup.add(blade);

    engineGroup.add(propGroup);
    propGroupRef.current = propGroup;

    camera.lookAt(0, 0, 0);

    // Mouse Interaction (Orbiting)
    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - prevMouseX;
      const deltaY = e.clientY - prevMouseY;
      engineGroup.rotation.y += deltaX * 0.008;
      engineGroup.rotation.x += deltaY * 0.008;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const domElement = renderer.domElement;
    domElement.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    // Resize handler
    const handleResize = () => {
      if (!mountRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // Animation Loop
    let animId: number;
    const animate = () => {
      animId = requestAnimationFrame(animate);

      // Rotate propeller proportional to RPM
      if (propGroupRef.current) {
        const rpm = typeof telemetry?.rpm === 'number' ? telemetry.rpm : 1400;
        propGroupRef.current.rotation.z += (rpm / 60) * 0.03;
      }

      // Gentle auto-hover oscillation
      engineGroup.position.y = Math.sin(Date.now() * 0.0015) * 0.05;

      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animId);
      domElement.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      window.removeEventListener('resize', handleResize);
      if (mountRef.current && renderer.domElement && mountRef.current.contains(renderer.domElement)) {
        mountRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Update dynamic colors based on health & telemetry
  useEffect(() => {
    if (!meshMapRef.current) return;

    // Helper for health to color
    const getHealthColor = (score: number) => {
      if (score >= 85) return 0x10b981; // Green
      if (score >= 65) return 0xf59e0b; // Amber
      return 0xef4444; // Red
    };

    // Update Cylinders
    for (let i = 1; i <= 4; i++) {
      const cylMesh = meshMapRef.current[`cyl_${i}`] as THREE.Mesh;
      if (cylMesh && cylMesh.material) {
        const cylMat = cylMesh.material as THREE.MeshStandardMaterial;
        const rawCht = (telemetry as any)?.[`cht_${i}`];
        const cht = typeof rawCht === 'number' ? rawCht : 120;
        // Elevated CHT turns amber/red
        if (cht > 220) {
          cylMat.color.setHex(0xef4444);
        } else if (cht > 180) {
          cylMat.color.setHex(0xf59e0b);
        } else {
          cylMat.color.setHex(0x06b6d4);
        }
      }
    }

    // Update Turbo
    const turboMesh = meshMapRef.current['turbo'] as THREE.Mesh;
    if (turboMesh && turboMesh.material) {
      const turboMat = turboMesh.material as THREE.MeshStandardMaterial;
      const turboHealth = typeof health?.turbo === 'number' ? health.turbo : 100;
      turboMat.color.setHex(getHealthColor(turboHealth));
    }

    // Update Sump / Lubrication
    const sumpMesh = meshMapRef.current['oil_sump'] as THREE.Mesh;
    if (sumpMesh && sumpMesh.material) {
      const sumpMat = sumpMesh.material as THREE.MeshStandardMaterial;
      const lubHealth = typeof health?.lubrication === 'number' ? health.lubrication : 100;
      sumpMat.color.setHex(getHealthColor(lubHealth));
    }
  }, [telemetry, health, activeFaults]);

  return (
    <div className="relative w-full h-full min-h-[300px] bg-[#070b13] rounded-xl border border-slate-800 overflow-hidden flex flex-col">
      {/* 3D Viewport Title & Controls */}
      <div className="absolute top-3 left-4 z-10 pointer-events-none">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
          <h3 className="font-mono text-xs font-semibold text-cyan-400 uppercase tracking-wider">
            3D Physical Engine Digital Twin
          </h3>
        </div>
        <p className="text-[11px] text-slate-400 mt-0.5">Rotax 914 Class • Drag to orbit • Scroll to zoom</p>
      </div>

      {/* Component Status Legend */}
      <div className="absolute top-3 right-4 z-10 flex items-center gap-3 bg-[#0d131f]/90 border border-slate-800/80 px-3 py-1.5 rounded-lg text-[10px] font-mono backdrop-blur-sm">
        <span className="flex items-center gap-1.5 text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Normal
        </span>
        <span className="flex items-center gap-1.5 text-amber-400">
          <span className="w-2 h-2 rounded-full bg-amber-500"></span> Caution
        </span>
        <span className="flex items-center gap-1.5 text-rose-400">
          <span className="w-2 h-2 rounded-full bg-rose-500"></span> Degraded
        </span>
      </div>

      {/* Three.js Canvas Container */}
      <div ref={mountRef} className="w-full flex-1 cursor-grab active:cursor-grabbing" />

      {/* Live Subsystem Inspection Bar */}
      <div className="bg-[#0b101b]/95 border-t border-slate-800/80 px-4 py-2 flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-4 text-slate-300">
          <span>CYL 1: {telemetry?.cht_1 ? `${telemetry.cht_1.toFixed(0)}°C` : '120°C'}</span>
          <span>CYL 2: {telemetry?.cht_2 ? `${telemetry.cht_2.toFixed(0)}°C` : '120°C'}</span>
          <span>CYL 3: {telemetry?.cht_3 ? `${telemetry.cht_3.toFixed(0)}°C` : '120°C'}</span>
          <span>CYL 4: {telemetry?.cht_4 ? `${telemetry.cht_4.toFixed(0)}°C` : '120°C'}</span>
        </div>
        <div className="text-cyan-400 text-[11px]">
          OIL: {telemetry?.oil_pressure_psi ? `${telemetry.oil_pressure_psi.toFixed(1)} psi` : '58.0 psi'} | TURBO:{' '}
          {telemetry?.turbo_boost_psi ? `${telemetry.turbo_boost_psi.toFixed(1)} psi` : '0.0 psi'}
        </div>
      </div>
    </div>
  );
};
