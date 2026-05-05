/**
 * Map a normalized score (0.0 to 1.0) to a heatmap color hex string.
 * Low values (0.0) are cooler colors (e.g., blue).
 * High values (1.0) are warmer colors (e.g., red).
 */
export function scoreToHeatmapColor(score) {
  // Clamp score between 0 and 1
  const s = Math.max(0, Math.min(1, score));
  
  // Blue (240 hue) to Red (0 hue)
  const hue = (1 - s) * 240;
  
  // Convert HSL to Hex
  const h = hue / 360;
  const s_adj = 0.9;
  const l = 0.55;
  
  let r, g, b;
  if (s_adj === 0) {
    r = g = b = l; // achromatic
  } else {
    const hue2rgb = (p, q, t) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };
    
    const q = l < 0.5 ? l * (1 + s_adj) : l + s_adj - l * s_adj;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1/3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1/3);
  }
  
  const toHex = (x) => {
    const hex = Math.round(x * 255).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  };
  
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}
