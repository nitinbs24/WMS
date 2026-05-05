import { useState, useEffect } from 'react';
import Layout from './components/ui/Layout';
import Scene from './components/3d/Scene';
import BinTooltip from './components/3d/BinTooltip';
import useWarehouseStore from './store/useWarehouseStore';
import { stopAutoSimulation } from './simulator/mockDataGenerator';

/**
 * App — Root Component
 *
 * Owns top-level UI state:
 *  - cameraMode:    'perspective' | 'top'
 *  - selectedBinId: which bin the user clicked (null = none)
 *
 * Data flows:
 *  Zustand store ──► Layout (stats, controls)
 *  Zustand store ──► Scene ──► InstancedBins (renders bins)
 *  click event   ──► selectedBinId ──► BinTooltip (3D popup)
 */
export default function App() {
  const [cameraMode, setCameraMode] = useState('perspective');
  const [selectedBinId, setSelectedBinId] = useState(null);

  const selectedBin = useWarehouseStore((s) =>
    selectedBinId ? s.bins[selectedBinId] ?? null : null
  );

  const handleCameraToggle = () =>
    setCameraMode((m) => (m === 'perspective' ? 'top' : 'perspective'));

  const handleBinClick = (binId) =>
    setSelectedBinId((prev) => (prev === binId ? null : binId));

  const handleTooltipClose = () => setSelectedBinId(null);

  // Cleanup simulator on unmount
  useEffect(() => () => stopAutoSimulation(), []);

  return (
    <Layout cameraMode={cameraMode} onCameraToggle={handleCameraToggle}>
      <Scene cameraMode={cameraMode} onBinClick={handleBinClick}>
        {selectedBin && (
          <BinTooltip bin={selectedBin} onClose={handleTooltipClose} />
        )}
      </Scene>
    </Layout>
  );
}
