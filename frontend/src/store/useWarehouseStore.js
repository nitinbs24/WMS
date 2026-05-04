import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

/**
 * Warehouse Digital Twin — Zustand Global Store
 * 
 * Central state management for the 3D warehouse visualization.
 * All WebSocket payloads flow into this store. Components subscribe
 * to specific slices via selectors to minimize re-renders.
 * 
 * State Shape:
 *   bins         — Map<bin_id, BinData>
 *   paths        — Current A* walking path coordinates
 *   pickSequence — Ordered bin IDs for current pick order
 *   slottingSuggestions — Recommended bin relocations
 *   errors       — Collision errors and system alerts
 *   connectionStatus — WebSocket connection state
 *   lastTimestamp — Last received event timestamp (for resync)
 *   warehouseConfig — Configurable warehouse dimensions
 */

const DEFAULT_WAREHOUSE_CONFIG = {
  aisles: 4,
  racksPerAisle: 5,
  levelsPerRack: 3,
  aisleWidth: 3.0,      // meters
  rackWidth: 1.2,       // meters
  rackDepth: 0.8,       // meters
  levelHeight: 1.5,     // meters
  floorWidth: 40,       // total floor width in meters
  floorDepth: 30,       // total floor depth in meters
};

const useWarehouseStore = create(
  subscribeWithSelector((set, get) => ({
    // ── Bin State ──────────────────────────────────────────────
    bins: {},

    updateBin: (binData) =>
      set((state) => ({
        bins: {
          ...state.bins,
          [binData.bin_id]: {
            ...state.bins[binData.bin_id],
            ...binData,
          },
        },
        lastTimestamp: binData.timestamp || state.lastTimestamp,
      })),

    removeBin: (binId) =>
      set((state) => {
        const { [binId]: _, ...rest } = state.bins;
        return { bins: rest };
      }),

    // ── Path State ────────────────────────────────────────────
    paths: [],
    pickSequence: [],

    setPath: (pathCoords) =>
      set({ paths: pathCoords }),

    setPickSequence: (sequence) =>
      set({ pickSequence: sequence }),

    clearPath: () =>
      set({ paths: [], pickSequence: [] }),

    // ── Slotting Suggestions ──────────────────────────────────
    slottingSuggestions: [],

    addSlottingSuggestion: (suggestion) =>
      set((state) => ({
        slottingSuggestions: [...state.slottingSuggestions, suggestion],
      })),

    clearSlottingSuggestions: () =>
      set({ slottingSuggestions: [] }),

    // ── Error State ───────────────────────────────────────────
    errors: [],

    addError: (error) =>
      set((state) => ({
        errors: [
          { ...error, id: Date.now(), dismissedAt: null },
          ...state.errors,
        ].slice(0, 50), // keep last 50 errors
      })),

    dismissError: (errorId) =>
      set((state) => ({
        errors: state.errors.map((e) =>
          e.id === errorId ? { ...e, dismissedAt: Date.now() } : e
        ),
      })),

    clearErrors: () =>
      set({ errors: [] }),

    // ── Connection State ──────────────────────────────────────
    connectionStatus: 'disconnected', // 'connected' | 'connecting' | 'disconnected'

    setConnectionStatus: (status) =>
      set({ connectionStatus: status }),

    // ── Timestamps ────────────────────────────────────────────
    lastTimestamp: null,

    // ── Warehouse Configuration ───────────────────────────────
    warehouseConfig: DEFAULT_WAREHOUSE_CONFIG,

    setWarehouseConfig: (config) =>
      set({ warehouseConfig: { ...DEFAULT_WAREHOUSE_CONFIG, ...config } }),

    // ── Heatmap Mode ──────────────────────────────────────────
    heatmapMode: 'occupancy', // 'occupancy' | 'velocity'

    setHeatmapMode: (mode) =>
      set({ heatmapMode: mode }),

    // ── Full State Operations ─────────────────────────────────
    fullResync: (warehouseState) => {
      const bins = {};
      if (warehouseState.bins && Array.isArray(warehouseState.bins)) {
        warehouseState.bins.forEach((bin) => {
          bins[bin.bin_id] = bin;
        });
      }
      set({
        bins,
        paths: warehouseState.paths || [],
        pickSequence: warehouseState.pick_sequence || [],
        slottingSuggestions: warehouseState.slotting_suggestions || [],
        errors: [],
        lastTimestamp: warehouseState.timestamp || Date.now(),
      });
    },

    resetState: () =>
      set({
        bins: {},
        paths: [],
        pickSequence: [],
        slottingSuggestions: [],
        errors: [],
        connectionStatus: 'disconnected',
        lastTimestamp: null,
        heatmapMode: 'occupancy',
      }),

    // ── Selectors (computed values) ───────────────────────────
    getBinById: (binId) => get().bins[binId] || null,
    getBinCount: () => Object.keys(get().bins).length,
    getActivErrors: () => get().errors.filter((e) => !e.dismissedAt),
  }))
);

export default useWarehouseStore;
export { DEFAULT_WAREHOUSE_CONFIG };
