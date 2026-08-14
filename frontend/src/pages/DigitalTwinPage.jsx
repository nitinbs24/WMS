/**
 * 3D Digital Twin Page
 * Three.js warehouse visualisation via @react-three/fiber + @react-three/drei.
 *
 * Data flow:
 *   GET /layout          → builds warehouse geometry (racks, slots)
 *   GET /runs            → latest completed run id
 *   GET /runs/{id}/assignments → slot colour overlay
 *
 * Slot colours:
 *   empty    → dark grey (#1e293b)
 *   occupied → teal gradient by score
 *   exception→ amber
 *
 * Controls: OrbitControls (mouse drag/zoom/pan), slot tooltip on hover.
 */
import { Suspense, useMemo, useRef, useState, useCallback } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Html, Grid, Environment } from '@react-three/drei';
import { useQuery } from '@tanstack/react-query';
import * as THREE from 'three';
import { runsApi } from '../api/runs';
import { api } from '../api/client';

// ─── palette ───────────────────────────────────────────────────────────────
const COLORS = {
  empty:       new THREE.Color('#1e293b'),
  occupied:    new THREE.Color('#0ea5e9'),
  exception:   new THREE.Color('#f59e0b'),
  rack:        new THREE.Color('#334155'),
  floor:       new THREE.Color('#0f172a'),
  highlight:   new THREE.Color('#38bdf8'),
};

// ─── data hooks ────────────────────────────────────────────────────────────
function useLayout() {
  return useQuery({
    queryKey: ['layout'],
    queryFn: async () => {
      const list = await api.get('/api/v1/layout');
      // API returns list[WarehouseOut] — use the first warehouse
      return Array.isArray(list) ? list[0] ?? null : list;
    },
    staleTime: 60_000,
  });
}

function useLatestRunAssignments() {
  const { data: runs = [] } = useQuery({
    queryKey: ['runs'],
    queryFn: runsApi.list,
    staleTime: 10_000,
  });
  const latestCompleted = runs.find(r =>
    r.status === 'completed' || r.status === 'completed_with_exceptions'
  );
  const { data: assignments = [] } = useQuery({
    queryKey: ['assignments', latestCompleted?.id],
    queryFn: () => runsApi.assignments(latestCompleted.id),
    enabled: !!latestCompleted,
    staleTime: 30_000,
  });
  const { data: exceptions = [] } = useQuery({
    queryKey: ['exceptions', latestCompleted?.id],
    queryFn: () => runsApi.exceptions(latestCompleted.id),
    enabled: !!latestCompleted,
    staleTime: 30_000,
  });
  return { assignments, exceptions, runId: latestCompleted?.id };
}

// ─── InstancedSlots ─────────────────────────────────────────────────────────
function InstancedSlots({ slots, assignmentMap, exceptionSet, onHover, onClickSlot }) {
  const meshRef = useRef();
  const count = slots.length;

  const { dummy, colorArray } = useMemo(() => {
    const dummy = new THREE.Object3D();
    const colorArray = new Float32Array(count * 3);
    return { dummy, colorArray };
  }, [count]);

  useMemo(() => {
    if (!meshRef.current) return;
    const c = new THREE.Color();
    slots.forEach((slot, i) => {
      const isException = exceptionSet.has(slot.id);
      const assignment = assignmentMap.get(slot.id);
      const isOccupied = !!assignment;

      dummy.position.set(
        parseFloat(slot.pos_x) * 3,
        parseFloat(slot.pos_z || slot.level * 2.2),
        parseFloat(slot.pos_y) * 3
      );
      dummy.scale.setScalar(1);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);

      if (isException) c.copy(COLORS.exception);
      else if (isOccupied) {
        const score = assignment.score ?? 0.8;
        c.lerpColors(COLORS.occupied, new THREE.Color('#818cf8'), score);
      } else {
        c.copy(COLORS.empty);
      }
      c.toArray(colorArray, i * 3);
      meshRef.current.setColorAt(i, c);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) meshRef.current.instanceColor.needsUpdate = true;
  }, [slots, assignmentMap, exceptionSet, dummy, colorArray]);

  const handlePointerMove = useCallback((e) => {
    e.stopPropagation();
    const i = e.instanceId;
    if (i !== undefined) onHover(slots[i], e.point);
  }, [slots, onHover]);

  const handlePointerOut = useCallback(() => onHover(null), [onHover]);
  const handleClick = useCallback((e) => {
    e.stopPropagation();
    if (e.instanceId !== undefined) onClickSlot(slots[e.instanceId]);
  }, [slots, onClickSlot]);

  return (
    <instancedMesh
      ref={meshRef}
      args={[null, null, count]}
      onPointerMove={handlePointerMove}
      onPointerOut={handlePointerOut}
      onClick={handleClick}
      castShadow
    >
      <boxGeometry args={[0.85, 1.8, 0.85]} />
      <meshStandardMaterial vertexColors roughness={0.4} metalness={0.3} />
    </instancedMesh>
  );
}

// ─── RackFrame ──────────────────────────────────────────────────────────────
function RackFrame({ rack }) {
  const levels = rack.levels ?? 4;
  const px = parseFloat(rack.pos_x) * 3;
  const pz = parseFloat(rack.pos_y) * 3;
  return (
    <mesh position={[px, levels * 1.1, pz]} castShadow>
      <boxGeometry args={[0.1, levels * 2.2, 0.1]} />
      <meshStandardMaterial color={COLORS.rack} roughness={0.8} />
    </mesh>
  );
}

// ─── SlotTooltip ────────────────────────────────────────────────────────────
function SlotTooltip({ slot, point, assignmentMap, exceptionSet }) {
  if (!slot) return null;
  const assignment = assignmentMap.get(slot.id);
  const isException = exceptionSet.has(slot.id);
  return (
    <Html position={[point.x, point.y + 1.5, point.z]} center distanceFactor={12}>
      <div style={{
        background: 'rgba(15,23,42,0.95)',
        border: '1px solid rgba(56,189,248,0.3)',
        borderRadius: 8,
        padding: '10px 14px',
        minWidth: 160,
        pointerEvents: 'none',
        backdropFilter: 'blur(10px)',
        color: '#f1f5f9',
        fontSize: 12,
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      }}>
        <div style={{ fontWeight: 700, marginBottom: 6, color: '#38bdf8' }}>
          Slot — Level {slot.level}
        </div>
        <div style={{ color: '#94a3b8', marginBottom: 2 }}>
          Status: <span style={{ color: isException ? '#f59e0b' : assignment ? '#10b981' : '#64748b' }}>
            {isException ? 'exception' : assignment ? 'occupied' : 'empty'}
          </span>
        </div>
        {assignment && (
          <div style={{ color: '#94a3b8' }}>
            Score: <span style={{ color: '#a5f3fc' }}>{(assignment.score ?? 0).toFixed(3)}</span>
          </div>
        )}
        <div style={{ color: '#475569', fontSize: 10, marginTop: 4 }}>
          cap {slot.clearance_height}m · {slot.weight_capacity}kg
        </div>
      </div>
    </Html>
  );
}

// ─── Scene ─────────────────────────────────────────────────────────────────
function Scene({ layout, assignments, exceptions }) {
  const [hoverSlot, setHoverSlot] = useState(null);
  const [hoverPoint, setHoverPoint] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState(null);

  const { slots, racks } = useMemo(() => {
    if (!layout) return { slots: [], racks: [] };
    const slots = [];
    const racks = [];
    (layout.aisles || []).forEach(aisle => {
      (aisle.racks || []).forEach(rack => {
        racks.push(rack);
        (rack.slots || []).forEach(slot => slots.push(slot));
      });
    });
    return { slots, racks };
  }, [layout]);

  const assignmentMap = useMemo(() => {
    const m = new Map();
    assignments.forEach(a => m.set(a.slot_id, a));
    return m;
  }, [assignments]);

  const exceptionSet = useMemo(() => {
    const s = new Set();
    exceptions.forEach(e => { if (e.slot_id) s.add(e.slot_id); });
    return s;
  }, [exceptions]);

  const handleHover = useCallback((slot, point) => {
    setHoverSlot(slot ?? null);
    setHoverPoint(point ?? null);
  }, []);

  if (!slots.length) return null;

  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight position={[20, 30, 20]} intensity={1.2} castShadow />
      <pointLight position={[-10, 20, -10]} intensity={0.5} color="#818cf8" />

      <Grid
        args={[100, 100]}
        position={[0, -0.05, 0]}
        cellColor="#1e293b"
        sectionColor="#334155"
        fadeDistance={60}
        infiniteGrid
      />

      {/* Rack frames */}
      {racks.map(rack => <RackFrame key={rack.id} rack={rack} />)}

      {/* Instanced slots */}
      {slots.length > 0 && (
        <InstancedSlots
          slots={slots}
          assignmentMap={assignmentMap}
          exceptionSet={exceptionSet}
          onHover={handleHover}
          onClickSlot={setSelectedSlot}
        />
      )}

      {/* Tooltip */}
      {hoverSlot && hoverPoint && (
        <SlotTooltip
          slot={hoverSlot}
          point={hoverPoint}
          assignmentMap={assignmentMap}
          exceptionSet={exceptionSet}
        />
      )}

      <OrbitControls
        makeDefault
        minDistance={3}
        maxDistance={120}
        maxPolarAngle={Math.PI / 2.1}
        dampingFactor={0.07}
        enableDamping
      />
    </>
  );
}

// ─── Legend ─────────────────────────────────────────────────────────────────
function Legend({ assignments, exceptions, slotCount }) {
  return (
    <div style={{
      position: 'absolute', bottom: 20, left: 20,
      background: 'rgba(15,23,42,0.85)',
      border: '1px solid rgba(56,189,248,0.15)',
      borderRadius: 10, padding: '14px 18px',
      backdropFilter: 'blur(12px)',
      display: 'flex', flexDirection: 'column', gap: 8,
      minWidth: 200,
    }}>
      <div style={{ color: '#94a3b8', fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4 }}>
        Legend
      </div>
      {[
        { color: '#1e293b', label: 'Empty', count: slotCount - assignments.length - exceptions.length },
        { color: '#0ea5e9', label: 'Occupied', count: assignments.length },
        { color: '#f59e0b', label: 'Exception', count: exceptions.length },
      ].map(({ color, label, count }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: color, border: '1px solid rgba(255,255,255,0.1)', flexShrink: 0 }} />
          <span style={{ color: '#e2e8f0', fontSize: 13, flex: 1 }}>{label}</span>
          <span style={{ color: '#64748b', fontSize: 12, fontVariantNumeric: 'tabular-nums' }}>{Math.max(0, count)}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────
export default function DigitalTwinPage() {
  const { data: layout, isLoading: layoutLoading, error: layoutError } = useLayout();
  const { assignments, exceptions, runId } = useLatestRunAssignments();

  const slotCount = useMemo(() => {
    if (!layout) return 0;
    return (layout.aisles || []).reduce((acc, a) =>
      acc + (a.racks || []).reduce((ra, r) => ra + (r.slots || []).length, 0), 0
    );
  }, [layout]);

  return (
    <div style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div className="page-header" style={{ flexShrink: 0 }}>
        <div>
          <h2>3D Digital Twin</h2>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>
            {runId ? `Showing assignments from run ${runId.slice(0, 8)}…` : 'No completed run yet — layout only'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: 'var(--color-surface)', borderRadius: 8, fontSize: 12, color: 'var(--color-text-muted)', border: '1px solid var(--color-border-subtle)' }}>
            <span>🖱</span> Drag to orbit · Scroll to zoom · Right-click to pan
          </div>
        </div>
      </div>

      {/* Canvas container */}
      <div style={{ flex: 1, position: 'relative', borderRadius: 12, overflow: 'hidden', border: '1px solid var(--color-border-subtle)' }}>
        {layoutLoading && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--color-surface)', zIndex: 10, flexDirection: 'column', gap: 12 }}>
            <div className="spinner" />
            <span style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>Loading warehouse layout…</span>
          </div>
        )}

        {layoutError && !layoutLoading && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--color-surface)', flexDirection: 'column', gap: 12 }}>
            <span style={{ fontSize: 40 }}>📦</span>
            <h3 style={{ color: 'var(--color-text)' }}>No layout imported yet</h3>
            <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>Import a warehouse layout via the API to see the 3D twin.</p>
          </div>
        )}

        {layout && (
          <Canvas
            camera={{ position: [15, 18, 25], fov: 50 }}
            shadows
            gl={{ antialias: true, alpha: false }}
            style={{ background: 'linear-gradient(180deg, #0a1628 0%, #0f172a 100%)' }}
          >
            <Suspense fallback={null}>
              <Scene layout={layout} assignments={assignments} exceptions={exceptions} />
            </Suspense>
          </Canvas>
        )}

        {layout && (
          <Legend assignments={assignments} exceptions={exceptions} slotCount={slotCount} />
        )}
      </div>
    </div>
  );
}
