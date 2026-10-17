"use client";

import type { ProfileStyle } from "@/lib/types";

const INKS = ["#1d4ed8", "#111111", "#1e3a8a", "#0f766e", "#7c3aed", "#b91c1c", "#78350f"];

export function StyleControls({
  style,
  onChange,
}: {
  style: ProfileStyle;
  onChange: (next: ProfileStyle) => void;
}) {
  return (
    <div className="stack">
      <div className="field">
        <label>Word size ({Math.round(style.word_size_px)}px)</label>
        <input
          type="range" min={40} max={110} step={1} value={style.word_size_px}
          onChange={(event) => onChange({ ...style, word_size_px: Number(event.target.value) })}
        />
      </div>
      <div className="field">
        <label>Word spacing ({Math.round(style.word_spacing_px)}px)</label>
        <input
          type="range" min={4} max={40} step={1} value={style.word_spacing_px}
          onChange={(event) => onChange({ ...style, word_spacing_px: Number(event.target.value) })}
        />
      </div>
      <div className="field">
        <label>Character spacing ({style.char_spacing_px.toFixed(1)}px)</label>
        <input
          type="range" min={-8} max={16} step={0.5} value={style.char_spacing_px}
          onChange={(event) => onChange({ ...style, char_spacing_px: Number(event.target.value) })}
        />
      </div>
      <div className="field">
        <label>Variation ({style.variation.toFixed(2)})</label>
        <input
          type="range" min={0} max={0.5} step={0.05} value={style.variation}
          onChange={(event) => onChange({ ...style, variation: Number(event.target.value) })}
        />
      </div>
      <div className="field">
        <label>Output ink color</label>
        <p className="secondary">Leave unset to keep the colors you drew.</p>
        <div className="ink-row">
          <button
            type="button"
            className={style.ink_color ? "ink-swatch" : "ink-swatch on"}
            onClick={() => onChange({ ...style, ink_color: null })}
            aria-label="Original ink"
          >Aa</button>
          {INKS.map((color) => (
            <button
              key={color}
              type="button"
              className={style.ink_color === color ? "ink-swatch on" : "ink-swatch"}
              style={{ background: color }}
              aria-label={color}
              onClick={() => onChange({ ...style, ink_color: color })}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
