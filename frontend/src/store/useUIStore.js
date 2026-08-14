import { create } from 'zustand';

/**
 * UI-only state store — camera mode, selected slot, active overlay, 3D scene controls.
 * No server data here; all server state via TanStack Query.
 */
export const useUIStore = create((set) => ({
  // 3D camera
  cameraMode: 'perspective',          // 'perspective' | 'top'
  setCameraMode: (mode) => set({ cameraMode: mode }),
  toggleCamera: () => set((s) => ({ cameraMode: s.cameraMode === 'perspective' ? 'top' : 'perspective' })),

  // Selected slot in 3D view
  selectedSlotId: null,
  setSelectedSlotId: (id) => set({ selectedSlotId: id }),
  clearSelectedSlot: () => set({ selectedSlotId: null }),

  // Heatmap overlay mode
  overlayMode: 'none',               // 'none' | 'fill_rate' | 'pick_frequency' | 'weight_class' | 'aisle_direction'
  setOverlayMode: (mode) => set({ overlayMode: mode }),

  // Before/after run comparison
  compareRunId: null,
  setCompareRunId: (id) => set({ compareRunId: id }),

  // Override drag state
  overrideDraft: null,               // { assignmentId, fromSlotId, toSlotId } | null
  setOverrideDraft: (draft) => set({ overrideDraft: draft }),
  clearOverrideDraft: () => set({ overrideDraft: null }),
}));
