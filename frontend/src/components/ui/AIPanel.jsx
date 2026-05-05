import React from 'react';
import { BrainCircuit, ArrowRight, TrendingUp } from 'lucide-react';
import useWarehouseStore from '../../store/useWarehouseStore';

export default function AIPanel() {
  const suggestions = useWarehouseStore((s) => s.slottingSuggestions);

  if (suggestions.length === 0) return null;

  // Show only the 4 most recent suggestions
  const recentSuggestions = [...suggestions].reverse().slice(0, 4);

  return (
    <div className="ai-panel">
      <div className="ai-panel__header">
        <BrainCircuit size={18} color="var(--accent-purple)" />
        <span className="ai-panel__title">AI Insights</span>
      </div>
      
      <div className="ai-panel__content">
        {recentSuggestions.map((sug, idx) => (
          <div key={`${sug.timestamp}-${idx}`} className="ai-suggestion">
            <div className="ai-suggestion__header">
              <span className="ai-suggestion__route">
                {sug.from_bin} <ArrowRight size={12} /> {sug.to_bin}
              </span>
              <span className="ai-suggestion__impact">
                <TrendingUp size={12} /> {sug.improvement_pct.toFixed(1)}%
              </span>
            </div>
            <p className="ai-suggestion__reason">{sug.reason}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
