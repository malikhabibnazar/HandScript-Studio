"use client";

import { glyphImageUrl } from "@/lib/api";
import type { GlyphGroup, GlyphInventory, GlyphSetName } from "@/lib/types";

const ORDER: GlyphGroup[] = ["uppercase", "lowercase", "symbols"];
const TITLE: Record<GlyphGroup, string> = {
  uppercase: "Uppercase",
  lowercase: "Lowercase",
  symbols: "Numbers & symbols",
};

function isGroup(value: string): value is GlyphGroup {
  return value === "uppercase" || value === "lowercase" || value === "symbols";
}

export function CharacterGrid({
  profileId,
  inventory,
  setName,
  selectedKey,
  stamp,
  onSelect,
}: {
  profileId: string;
  inventory: GlyphInventory;
  setName: GlyphSetName;
  selectedKey: string;
  stamp: number;
  onSelect: (key: string) => void;
}) {
  return (
    <div className="stack">
      {ORDER.map((group) => {
        const slots = inventory.slots.filter((slot) => isGroup(slot.group) && slot.group === group);
        if (slots.length === 0) return null;
        return (
          <details key={group} open className="glyph-group">
            <summary>{TITLE[group]}</summary>
            <div className="glyph-grid">
              {slots.map((slot) => {
                const metrics = setName === "set1" ? slot.set1 : slot.set2;
                const on = slot.key === selectedKey;
                return (
                  <button
                    key={slot.key}
                    type="button"
                    className={on ? "glyph-key on" : metrics ? "glyph-key filled" : "glyph-key"}
                    onClick={() => onSelect(slot.key)}
                  >
                    {metrics ? (
                      <img src={glyphImageUrl(profileId, setName, slot.key, stamp)} alt="" />
                    ) : (
                      <span>{slot.char}</span>
                    )}
                  </button>
                );
              })}
            </div>
          </details>
        );
      })}
    </div>
  );
}
