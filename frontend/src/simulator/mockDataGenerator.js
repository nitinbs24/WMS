import useWarehouseStore, { DEFAULT_WAREHOUSE_CONFIG } from '../store/useWarehouseStore';

/**
 * Mock Data Generator
 * 
 * Generates fake WebSocket-compatible JSON payloads matching the 
 * agreed contract. Enables Person B to develop the entire frontend
 * independently without Person A's backend.
 * 
 * Modes:
 *   - generateInitialState()  → Full warehouse with bins across racks
 *   - emitRandomBinUpdate()   → Single bin occupancy/position change
 *   - emitOrderPath()         → A* walking path with pick sequence
 *   - emitSlottingSuggestion() → Recommended bin relocation
 *   - emitCollisionError()    → Collision detection alert
 *   - startAutoSimulation()   → Continuous random events at interval
 */

// ── Helper Utilities ───────────────────────────────────────────

const ERGONOMIC_ZONES = ['golden', 'upper', 'lower', 'floor'];
const SKU_PREFIXES = ['SKU', 'WH', 'PLT', 'BLK', 'CRT'];

function randomFloat(min, max) {
  return Math.round((Math.random() * (max - min) + min) * 100) / 100;
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomChoice(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function generateBinId(aisle, rack, level) {
  const aisleLabel = String.fromCharCode(65 + aisle); // A, B, C, D...
  const rackLabel = String(rack + 1).padStart(2, '0');
  const levelLabel = String(level + 1).padStart(2, '0');
  return `${aisleLabel}-${rackLabel}-${levelLabel}`;
}

function occupancyToColor(pct) {
  if (pct <= 50) return '#22c55e';
  if (pct <= 75) return '#f59e0b';
  if (pct <= 90) return '#f97316';
  return '#ef4444';
}

function getErgonomicZone(level, totalLevels) {
  if (totalLevels <= 1) return 'golden';
  const ratio = level / (totalLevels - 1);
  if (ratio < 0.25) return 'floor';
  if (ratio < 0.6) return 'golden';
  if (ratio < 0.85) return 'upper';
  return 'upper';
}

// ── Position Calculation ───────────────────────────────────────

function calculateBinPosition(aisle, rack, level, config = DEFAULT_WAREHOUSE_CONFIG) {
  const { aisleWidth, rackWidth, rackDepth, levelHeight } = config;

  const rackSpacing  = rackWidth + 0.3;       // spacing between bays along Z
  const aisleSpacing = rackDepth * 2 + aisleWidth; // spacing between aisles along X

  // Place bins on the FRONT rack row of each aisle
  // Front rack row X center = aisleX + rackDepth/2
  const aisleX = aisle * aisleSpacing;
  const x = aisleX + rackDepth / 2;

  // Z center of this rack bay
  const rackZ = rack * rackSpacing + rackWidth / 2;
  const z = rackZ;

  // Y center of this level
  const y = level * levelHeight + levelHeight / 2;

  return { x, y, z };
}

// ── Generator Functions ────────────────────────────────────────

/**
 * Generate the complete initial warehouse state.
 * Creates bins across all aisles, racks, and levels with random occupancy.
 */
export function generateInitialState(config = DEFAULT_WAREHOUSE_CONFIG) {
  const { aisles, racksPerAisle, levelsPerRack } = config;
  const bins = [];

  for (let a = 0; a < aisles; a++) {
    for (let r = 0; r < racksPerAisle; r++) {
      for (let l = 0; l < levelsPerRack; l++) {
        const binId = generateBinId(a, r, l);
        const occupancy = randomInt(0, 100);
        const position = calculateBinPosition(a, r, l, config);

        bins.push({
          bin_id: binId,
          position,
          dimensions: {
            l: config.rackWidth,
            w: config.rackDepth,
            h: config.levelHeight,
          },
          occupancy_pct: occupancy,
          color_hex: occupancyToColor(occupancy),
          slot_score: randomFloat(0, 1),
          ergonomic_zone: getErgonomicZone(l, levelsPerRack),
          sku: `${randomChoice(SKU_PREFIXES)}-${randomInt(1000, 9999)}`,
          timestamp: Date.now(),
        });
      }
    }
  }

  return {
    event: 'FULL_RESYNC',
    bins,
    paths: [],
    pick_sequence: [],
    slotting_suggestions: [],
    timestamp: Date.now(),
  };
}

/**
 * Generate a random BIN_UPDATED event for an existing bin.
 */
export function generateRandomBinUpdate() {
  const store = useWarehouseStore.getState();
  const binIds = Object.keys(store.bins);

  if (binIds.length === 0) return null;

  const binId = randomChoice(binIds);
  const existingBin = store.bins[binId];
  const newOccupancy = Math.min(100, Math.max(0, existingBin.occupancy_pct + randomInt(-20, 20)));

  return {
    event: 'BIN_UPDATED',
    bin_id: binId,
    position: existingBin.position,
    dimensions: existingBin.dimensions,
    occupancy_pct: newOccupancy,
    color_hex: occupancyToColor(newOccupancy),
    slot_score: randomFloat(0, 1),
    ergonomic_zone: existingBin.ergonomic_zone,
    timestamp: Date.now(),
  };
}

/**
 * Generate an ORDER_PATH event with a walking path and pick sequence.
 */
export function generateOrderPath() {
  const store = useWarehouseStore.getState();
  const binIds = Object.keys(store.bins);

  if (binIds.length < 3) return null;

  // Pick 3-6 random bins for the pick sequence
  const pickCount = randomInt(3, Math.min(6, binIds.length));
  const shuffled = [...binIds].sort(() => Math.random() - 0.5);
  const pickSequence = shuffled.slice(0, pickCount);

  // Generate an A* style path between the pick locations
  const path = [];
  let currentX = 0;
  let currentZ = 0;

  for (const binId of pickSequence) {
    const bin = store.bins[binId];
    if (!bin) continue;

    const targetX = bin.position.x;
    const targetZ = bin.position.z;

    // Simulate grid-aligned movement (Manhattan-style)
    // Move along X first, then Z
    const stepsX = Math.abs(targetX - currentX);
    const stepsZ = Math.abs(targetZ - currentZ);
    const dirX = targetX > currentX ? 1 : -1;
    const dirZ = targetZ > currentZ ? 1 : -1;

    for (let i = 0; i < Math.ceil(stepsX); i++) {
      currentX += dirX * Math.min(1, stepsX - i);
      path.push({ x: Math.round(currentX * 10) / 10, z: currentZ });
    }
    for (let i = 0; i < Math.ceil(stepsZ); i++) {
      currentZ += dirZ * Math.min(1, stepsZ - i);
      path.push({ x: currentX, z: Math.round(currentZ * 10) / 10 });
    }
  }

  return {
    event: 'ORDER_PATH',
    path,
    pick_sequence: pickSequence,
    timestamp: Date.now(),
  };
}

/**
 * Generate a SLOTTING_SUGGESTION event.
 */
export function generateSlottingSuggestion() {
  const store = useWarehouseStore.getState();
  const binIds = Object.keys(store.bins);

  if (binIds.length < 2) return null;

  const fromBin = randomChoice(binIds);
  let toBin = randomChoice(binIds);
  while (toBin === fromBin) {
    toBin = randomChoice(binIds);
  }

  return {
    event: 'SLOTTING_SUGGESTION',
    from_bin: fromBin,
    to_bin: toBin,
    reason: randomChoice([
      'Higher pick frequency — move to golden zone',
      'Co-located SKU affinity detected',
      'Reduce travel distance by 23%',
      'Ergonomic optimization — lower heavy items',
    ]),
    improvement_pct: randomFloat(5, 35),
    timestamp: Date.now(),
  };
}

/**
 * Generate a COLLISION_ERROR event.
 */
export function generateCollisionError() {
  const store = useWarehouseStore.getState();
  const binIds = Object.keys(store.bins);

  if (binIds.length === 0) return null;

  const binId = randomChoice(binIds);

  return {
    event: 'COLLISION_ERROR',
    bin_id: binId,
    message: `Spatial collision detected at ${binId} — overlapping geometry with adjacent bin`,
    timestamp: Date.now(),
  };
}

// ── Auto-Simulation Controller ─────────────────────────────────

let simulationInterval = null;

/**
 * Start continuous random event simulation.
 * @param {number} intervalMs - Milliseconds between events (default 2000)
 */
export function startAutoSimulation(intervalMs = 2000) {
  stopAutoSimulation();

  const store = useWarehouseStore.getState();

  // Seed initial state if empty
  if (Object.keys(store.bins).length === 0) {
    const initialState = generateInitialState();
    store.fullResync(initialState);
    console.log('[Simulator] Seeded initial warehouse state:', Object.keys(store.bins).length, 'bins');
  }

  simulationInterval = setInterval(() => {
    const roll = Math.random();
    let event;

    if (roll < 0.6) {
      event = generateRandomBinUpdate();
    } else if (roll < 0.8) {
      event = generateOrderPath();
    } else if (roll < 0.95) {
      event = generateSlottingSuggestion();
    } else {
      event = generateCollisionError();
    }

    if (event) {
      // Route through the same handler logic as real WebSocket events
      const store = useWarehouseStore.getState();
      switch (event.event) {
        case 'BIN_UPDATED':
          store.updateBin(event);
          break;
        case 'ORDER_PATH':
          store.setPath(event.path || []);
          store.setPickSequence(event.pick_sequence || []);
          break;
        case 'SLOTTING_SUGGESTION':
          store.addSlottingSuggestion(event);
          break;
        case 'COLLISION_ERROR':
          store.addError({
            type: 'COLLISION',
            bin_id: event.bin_id,
            message: event.message,
            timestamp: event.timestamp,
          });
          break;
      }
    }
  }, intervalMs);

  console.log(`[Simulator] Auto-simulation started (interval: ${intervalMs}ms)`);
}

/**
 * Stop the auto-simulation.
 */
export function stopAutoSimulation() {
  if (simulationInterval) {
    clearInterval(simulationInterval);
    simulationInterval = null;
    console.log('[Simulator] Auto-simulation stopped');
  }
}

/**
 * Check if auto-simulation is running.
 */
export function isSimulationRunning() {
  return simulationInterval !== null;
}

export default {
  generateInitialState,
  generateRandomBinUpdate,
  generateOrderPath,
  generateSlottingSuggestion,
  generateCollisionError,
  startAutoSimulation,
  stopAutoSimulation,
  isSimulationRunning,
};
