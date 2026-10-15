"use client";

import { useEffect, useMemo, useState } from "react";
import { Layer, Line, Rect, Stage, Text } from "react-konva";
import type { Element } from "@/lib/types";

const PPI = 72;

export function DocumentCanvas({
  widthIn,
  heightIn,
  marginIn,
  elements,
  selectedId,
  zoom,
  showGrid,
  editable,
  onSelect,
  onChange,
}: {
  widthIn: number;
  heightIn: number;
  marginIn: number;
  elements: Element[];
  selectedId: string | null;
  zoom: number;
  showGrid: boolean;
  editable: boolean;
  onSelect: (id: string | null) => void;
  onChange?: (id: string, patch: Partial<Element>) => void;
}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const width = widthIn * PPI * zoom;
  const height = heightIn * PPI * zoom;
  const lines = useMemo(() => {
    if (!showGrid) return [];
    const out: number[][] = [];
    for (let x = 0; x <= widthIn; x += 0.5) out.push([x * PPI * zoom, 0, x * PPI * zoom, height]);
    for (let y = 0; y <= heightIn; y += 0.5) out.push([0, y * PPI * zoom, width, y * PPI * zoom]);
    return out;
  }, [showGrid, widthIn, heightIn, width, height, zoom]);

  if (!mounted) return <div className="canvas-stage" />;

  return (
    <div className="canvas-stage">
      <Stage width={width + 24} height={height + 24} onMouseDown={(event) => {
        if (event.target === event.target.getStage()) onSelect(null);
      }}>
        <Layer x={12} y={12}>
          <Rect width={width} height={height} fill="#ffffff" shadowColor="rgba(0,0,0,0.18)" shadowBlur={18} shadowOffsetY={6} />
          {lines.map((points, index) => (
            <Line key={index} points={points} stroke="#eceff3" strokeWidth={1} />
          ))}
          <Rect
            x={marginIn * PPI * zoom}
            y={marginIn * PPI * zoom}
            width={(widthIn - marginIn * 2) * PPI * zoom}
            height={(heightIn - marginIn * 2) * PPI * zoom}
            stroke="#c7cbd4"
            dash={[4, 4]}
          />
          {elements.filter((el) => el.visible).map((el) => {
            const selected = el.id === selectedId;
            if (el.type === "Divider") {
              return (
                <Line
                  key={el.id}
                  points={[el.x * PPI * zoom, el.y * PPI * zoom, (el.x + el.width) * PPI * zoom, el.y * PPI * zoom]}
                  stroke={selected ? "#2d6cdf" : "#8d93a0"}
                  strokeWidth={2}
                  onClick={() => onSelect(el.id)}
                />
              );
            }
            return (
              <Text
                key={el.id}
                x={el.x * PPI * zoom}
                y={el.y * PPI * zoom}
                width={el.width * PPI * zoom}
                height={el.height * PPI * zoom}
                text={el.content || el.name}
                fontSize={Math.max(10, el.font_size * zoom)}
                fontFamily="Segoe Script, Brush Script MT, cursive"
                fill="#1d1d1f"
                draggable={editable}
                onClick={() => onSelect(el.id)}
                onTap={() => onSelect(el.id)}
                onDragEnd={(event) => onChange?.(el.id, {
                  x: Math.max(0, event.target.x() / (PPI * zoom)),
                  y: Math.max(0, event.target.y() / (PPI * zoom)),
                })}
                stroke={selected ? "#2d6cdf" : undefined}
                strokeWidth={selected ? 0.6 : 0}
              />
            );
          })}
        </Layer>
      </Stage>
    </div>
  );
}
