"use client";

import { useEffect, useRef, useState } from "react";

export type InkExport = {
  blob: Blob;
  baselineY: number;
  padWidth: number;
  padHeight: number;
  cropLeft: number;
  cropTop: number;
};

type Point = { x: number; y: number };

function bounds(data: ImageData) {
  const { width, height, data: pixels } = data;
  let left = width;
  let top = height;
  let right = -1;
  let bottom = -1;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (pixels[(y * width + x) * 4 + 3] <= 16) continue;
      if (x < left) left = x;
      if (y < top) top = y;
      if (x > right) right = x;
      if (y > bottom) bottom = y;
    }
  }
  if (right < 0) return null;
  return { left, top, right, bottom };
}

export function DrawPad({
  padWidth,
  padHeight,
  baselineY,
  resetKey,
  onSave,
}: {
  padWidth: number;
  padHeight: number;
  baselineY: number;
  resetKey: string;
  onSave: (ink: InkExport) => Promise<void>;
}) {
  const guideRef = useRef<HTMLCanvasElement>(null);
  const inkRef = useRef<HTMLCanvasElement>(null);
  const drawing = useRef<Point | null>(null);
  const undo = useRef<ImageData[]>([]);
  const [busy, setBusy] = useState(false);
  const [hasInk, setHasInk] = useState(false);

  function context() {
    const canvas = inkRef.current;
    return canvas ? canvas.getContext("2d") : null;
  }

  function clearInk() {
    const ctx = context();
    const canvas = inkRef.current;
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    undo.current = [];
    setHasInk(false);
  }

  useEffect(() => {
    const canvas = guideRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "#b7cbe6";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(16, baselineY);
    ctx.lineTo(canvas.width - 16, baselineY);
    ctx.stroke();
  }, [baselineY, padWidth, padHeight]);

  useEffect(() => {
    clearInk();
  }, [resetKey, padWidth, padHeight]);

  function pointerPoint(event: React.PointerEvent<HTMLCanvasElement>): Point {
    const canvas = inkRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) * canvas.width) / rect.width,
      y: ((event.clientY - rect.top) * canvas.height) / rect.height,
    };
  }

  function remember() {
    const canvas = inkRef.current;
    const ctx = context();
    if (!canvas || !ctx) return;
    undo.current = [...undo.current.slice(-19), ctx.getImageData(0, 0, canvas.width, canvas.height)];
  }

  function strokeTo(point: Point) {
    const ctx = context();
    const from = drawing.current;
    if (!ctx || !from) return;
    ctx.strokeStyle = "#1a1a1a";
    ctx.lineWidth = 5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(point.x, point.y);
    ctx.stroke();
    drawing.current = point;
    setHasInk(true);
  }

  async function save() {
    const canvas = inkRef.current;
    const ctx = context();
    if (!canvas || !ctx) return;
    const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const box = bounds(pixels);
    if (!box) return;
    const width = box.right - box.left + 1;
    const height = box.bottom - box.top + 1;
    const crop = document.createElement("canvas");
    crop.width = width;
    crop.height = height;
    const cropCtx = crop.getContext("2d");
    if (!cropCtx) return;
    cropCtx.drawImage(canvas, box.left, box.top, width, height, 0, 0, width, height);
    const blob = await new Promise<Blob | null>((resolve) => crop.toBlob(resolve, "image/png"));
    if (!blob) return;
    setBusy(true);
    try {
      await onSave({
        blob,
        baselineY,
        padWidth: canvas.width,
        padHeight: canvas.height,
        cropLeft: box.left,
        cropTop: box.top,
      });
      clearInk();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="draw-pad">
      <div className="draw-pad-stage" style={{ width: padWidth, height: padHeight }}>
        <canvas ref={guideRef} width={padWidth} height={padHeight} className="draw-guide" />
        <canvas
          ref={inkRef}
          width={padWidth}
          height={padHeight}
          className="draw-ink"
          onPointerDown={(event) => {
            try { event.currentTarget.setPointerCapture(event.pointerId); } catch { /* capture is optional */ }
            remember();
            drawing.current = pointerPoint(event);
            strokeTo(pointerPoint(event));
          }}
          onPointerMove={(event) => {
            if (!drawing.current) return;
            strokeTo(pointerPoint(event));
          }}
          onPointerUp={() => { drawing.current = null; }}
          onPointerLeave={() => { drawing.current = null; }}
        />
      </div>
      <p className="secondary">Draw this one character on the line. Descenders can cross it. Leave a gap for the next letter.</p>
      <div className="row">
        <button type="button" className="btn secondary" onClick={() => {
          const canvas = inkRef.current;
          const ctx = context();
          const previous = undo.current.pop();
          if (!canvas || !ctx || !previous) {
            clearInk();
            return;
          }
          ctx.putImageData(previous, 0, 0);
          setHasInk(bounds(ctx.getImageData(0, 0, canvas.width, canvas.height)) !== null);
        }}>Undo</button>
        <button type="button" className="btn secondary" onClick={clearInk}>Clear</button>
        <button type="button" className="btn primary" disabled={!hasInk || busy} onClick={() => void save()}>Save letter</button>
      </div>
    </div>
  );
}
