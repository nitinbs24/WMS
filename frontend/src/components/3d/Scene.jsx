import { Suspense, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Grid, Environment } from '@react-three/drei';
import Warehouse from './Warehouse';
import InstancedBins from './InstancedBins';

/**
 * Scene — Main 3D Canvas
 *
 * Responsibilities:
 *  - Owns the R3F <Canvas> (WebGL context)
 *  - Sets up camera, lighting, and environment
 *  - Renders the static Warehouse geometry
 *  - Renders all instanced bins via InstancedBins
 *  - Exposes OrbitControls for mouse navigation
 *
 * Camera modes:
 *  - 'perspective' (default) — orbit freely in 3D
 *  - 'top'                   — locked top-down view (triggered from parent)
 */
export default function Scene({ cameraMode = 'perspective', onBinClick, children }) {
  const orbitRef = useRef();

  return (
    <Canvas
      shadows
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: false }}
      style={{ background: '#0a0e17' }}
      onCreated={({ gl }) => {
        gl.setClearColor('#0a0e17');
      }}
    >
      {/* ── Camera ────────────────────────────────────────── */}
      <PerspectiveCamera
        makeDefault
        position={cameraMode === 'top' ? [0, 40, 0] : [20, 18, 20]}
        fov={50}
        near={0.1}
        far={500}
      />

      {/* ── Controls ──────────────────────────────────────── */}
      <OrbitControls
        ref={orbitRef}
        enableDamping
        dampingFactor={0.05}
        minDistance={4}
        maxDistance={120}
        maxPolarAngle={cameraMode === 'top' ? 0 : Math.PI / 2.1}
        target={[8, 0, 8]}
      />

      {/* ── Lighting ──────────────────────────────────────── */}
      {/* Strong ambient so nothing is fully black */}
      <ambientLight intensity={1.8} color="#ddeeff" />

      {/* Main overhead sun — strong key light */}
      <directionalLight
        position={[15, 25, 15]}
        intensity={2.5}
        color="#ffffff"
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-far={100}
        shadow-camera-left={-30}
        shadow-camera-right={30}
        shadow-camera-top={30}
        shadow-camera-bottom={-30}
      />

      {/* Fill light from opposite side */}
      <directionalLight position={[-15, 12, -10]} intensity={1.2} color="#a0c4ff" />

      {/* Front fill so bins facing camera are always lit */}
      <directionalLight position={[0, 5, 30]} intensity={1.0} color="#ffffff" />

      {/* Overhead industrial point lights */}
      <pointLight position={[5,  10, 5]}  intensity={1.5} color="#ffffff" distance={40} />
      <pointLight position={[15, 10, 5]}  intensity={1.5} color="#ffffff" distance={40} />
      <pointLight position={[5,  10, 15]} intensity={1.5} color="#ffffff" distance={40} />
      <pointLight position={[15, 10, 15]} intensity={1.5} color="#ffffff" distance={40} />

      {/* ── Floor Grid ────────────────────────────────────── */}
      <Grid
        position={[0, 0.01, 0]}
        args={[60, 60]}
        cellSize={1}
        cellThickness={0.4}
        cellColor="#1e293b"
        sectionSize={5}
        sectionThickness={0.8}
        sectionColor="#334155"
        fadeDistance={80}
        fadeStrength={1}
        infiniteGrid
      />

      {/* ── 3D Scene Content ──────────────────────────────── */}
      <Suspense fallback={null}>
        <Warehouse />
        <InstancedBins onBinClick={onBinClick} />
        {children}
      </Suspense>
    </Canvas>
  );
}
