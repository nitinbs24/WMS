import { useMemo } from 'react';
import useWarehouseStore, { DEFAULT_WAREHOUSE_CONFIG } from '../../store/useWarehouseStore';

/**
 * Warehouse — Static Environment Geometry
 *
 * Renders the physical warehouse structure:
 *  - Solid floor plane
 *  - Rack uprights (vertical steel columns per rack position)
 *  - Aisle markers on the floor
 *
 * This component reads only warehouseConfig from the store.
 * It never re-renders due to bin occupancy changes.
 */

// ── Sub-components ─────────────────────────────────────────────

/** A single rack upright column */
function RackUpright({ position, height, color }) {
  return (
    <mesh position={position} castShadow receiveShadow>
      <boxGeometry args={[0.06, height, 0.06]} />
      <meshStandardMaterial color={color} metalness={0.7} roughness={0.3} />
    </mesh>
  );
}

/** A single horizontal shelf beam */
function ShelfBeam({ position, width, color }) {
  return (
    <mesh position={position} castShadow>
      <boxGeometry args={[0.05, 0.04, width]} />
      <meshStandardMaterial color={color} metalness={0.7} roughness={0.3} />
    </mesh>
  );
}

/** An aisle stripe on the floor */
function AisleStripe({ position, length, width }) {
  return (
    <mesh position={position} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
      <planeGeometry args={[width, length]} />
      <meshStandardMaterial
        color="#1e3a5f"
        transparent
        opacity={0.35}
        roughness={1}
      />
    </mesh>
  );
}

// ── Main Component ─────────────────────────────────────────────

export default function Warehouse() {
  const config = useWarehouseStore((s) => s.warehouseConfig) || DEFAULT_WAREHOUSE_CONFIG;

  const {
    aisles,
    racksPerAisle,
    levelsPerRack,
    aisleWidth,
    rackWidth,
    rackDepth,
    levelHeight,
    floorWidth,
    floorDepth,
  } = config;

  const rackColor = '#94a3b8';
  const beamColor = '#cbd5e1';
  const rackHeight = levelsPerRack * levelHeight;
  const rackSpacing = rackWidth + 0.3;
  const aisleSpacing = rackDepth * 2 + aisleWidth;

  // ── Build rack geometry ──────────────────────────────────────
  const { uprights, beams, aisleStripes } = useMemo(() => {
    const uprights = [];
    const beams = [];
    const aisleStripes = [];

    for (let a = 0; a < aisles; a++) {
      const aisleX = a * aisleSpacing;

      // Aisle floor stripe (between the two rack rows)
      aisleStripes.push({
        key: `aisle-${a}`,
        position: [aisleX + rackDepth + aisleWidth / 2, 0.02, (racksPerAisle * rackSpacing) / 2],
        length: racksPerAisle * rackSpacing + rackWidth,
        width: aisleWidth,
      });

      for (let r = 0; r < racksPerAisle; r++) {
        const rackZ = r * rackSpacing + rackWidth / 2;

        // Front rack row (near side of aisle)
        const frontX = aisleX;
        // Rear rack row (far side of aisle)
        const rearX = aisleX + rackDepth * 2 + aisleWidth;

        [frontX, rearX].forEach((bx, side) => {
          // 4 corner uprights per rack bay
          [0, rackWidth].forEach((zOff) => {
            uprights.push({
              key: `u-${a}-${r}-${side}-${zOff}`,
              position: [bx, rackHeight / 2, rackZ - rackWidth / 2 + zOff],
              height: rackHeight,
              color: rackColor,
            });
          });

          // Horizontal shelf beams at each level
          for (let l = 0; l <= levelsPerRack; l++) {
            beams.push({
              key: `b-${a}-${r}-${side}-${l}`,
              position: [bx, l * levelHeight, rackZ],
              width: rackWidth,
              color: beamColor,
            });
          }
        });
      }
    }

    return { uprights, beams, aisleStripes };
  }, [aisles, racksPerAisle, levelsPerRack, aisleWidth, rackWidth, rackDepth, levelHeight, aisleSpacing, rackSpacing, rackHeight, rackColor, beamColor]);

  return (
    <group name="warehouse">
      {/* ── Floor ─────────────────────────────────────────── */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[floorWidth / 4, 0, floorDepth / 4]} receiveShadow>
        <planeGeometry args={[floorWidth, floorDepth]} />
        <meshStandardMaterial
          color="#0f172a"
          roughness={0.9}
          metalness={0.05}
        />
      </mesh>

      {/* ── Aisle Stripes ─────────────────────────────────── */}
      {aisleStripes.map((s) => (
        <AisleStripe key={s.key} {...s} />
      ))}

      {/* ── Rack Uprights ─────────────────────────────────── */}
      {uprights.map((u) => (
        <RackUpright key={u.key} {...u} />
      ))}

      {/* ── Shelf Beams ───────────────────────────────────── */}
      {beams.map((b) => (
        <ShelfBeam key={b.key} {...b} />
      ))}
    </group>
  );
}
