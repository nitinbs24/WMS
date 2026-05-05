import { useMemo, useCallback, useRef } from 'react';
import * as THREE from 'three';
import useWarehouseStore from '../../store/useWarehouseStore';

/**
 * InstancedBins — Bin Renderer
 *
 * After extensive debugging, THREE.InstancedMesh instanceColor proved
 * unreliable across Three.js versions (color buffer not injected into
 * the shader when vertexColors is set post-compilation).
 *
 * Solution: Render each bin as an individual <mesh> with its own
 * MeshStandardMaterial. For 60–200 bins this is completely fine
 * (~100 draw calls vs the theoretical single call). Performance
 * is only a concern at thousands of objects — we can switch back
 * to InstancedMesh with a custom shader at that point.
 *
 * Each bin uses a memoized material per unique color_hex to minimize
 * material objects.
 */

const BIN_GEOMETRY = new THREE.BoxGeometry(1, 1, 1);

// Cache materials by hex string to avoid creating duplicate materials
const materialCache = new Map();
function getMaterial(hex) {
  const key = hex ?? '#22c55e';
  if (!materialCache.has(key)) {
    materialCache.set(key, new THREE.MeshStandardMaterial({
      color: new THREE.Color(key),
      roughness: 0.45,
      metalness: 0.08,
    }));
  }
  return materialCache.get(key);
}

function Bin({ bin, onClick }) {
  const { position, dimensions, color_hex } = bin;
  const mat = useMemo(() => getMaterial(color_hex), [color_hex]);

  const w = (dimensions?.l ?? 1.2) * 0.86;
  const h = (dimensions?.h ?? 1.5) * 0.84;
  const d = (dimensions?.w ?? 0.8) * 0.86;

  return (
    <mesh
      geometry={BIN_GEOMETRY}
      material={mat}
      position={[position?.x ?? 0, position?.y ?? 0, position?.z ?? 0]}
      scale={[w, h, d]}
      castShadow
      receiveShadow
      onClick={(e) => { e.stopPropagation(); onClick?.(bin.bin_id); }}
    />
  );
}

export default function InstancedBins({ onBinClick }) {
  const bins     = useWarehouseStore((s) => s.bins);
  const binArray = useMemo(() => Object.values(bins), [bins]);

  return (
    <group name="bins">
      {binArray.map((bin) => (
        <Bin key={bin.bin_id} bin={bin} onClick={onBinClick} />
      ))}
    </group>
  );
}
