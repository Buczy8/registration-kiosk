import { useEffect, useRef, useState } from "react";

const MIN_STROKE_LENGTH = 40;
const STROKE_WIDTH = 2.5;
const STROKE_COLOR = "#111827";

function getPoint(event, canvas) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
}

function strokeLength(points) {
  let total = 0;
  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const current = points[index];
    total += Math.hypot(current.x - previous.x, current.y - previous.y);
  }
  return total;
}

function totalStrokeLength(strokes) {
  return strokes.reduce((sum, points) => sum + strokeLength(points), 0);
}

function drawStroke(context, points) {
  if (points.length < 2) {
    return;
  }

  context.beginPath();
  context.moveTo(points[0].x, points[0].y);

  for (let index = 1; index < points.length - 1; index += 1) {
    const current = points[index];
    const next = points[index + 1];
    const midX = (current.x + next.x) / 2;
    const midY = (current.y + next.y) / 2;
    context.quadraticCurveTo(current.x, current.y, midX, midY);
  }

  const last = points[points.length - 1];
  context.lineTo(last.x, last.y);
  context.stroke();
}

function redrawCanvas(canvas, strokes) {
  const rect = canvas.getBoundingClientRect();
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, rect.width, rect.height);
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, rect.width, rect.height);
  context.lineCap = "round";
  context.lineJoin = "round";
  context.strokeStyle = STROKE_COLOR;
  context.lineWidth = STROKE_WIDTH;

  for (const points of strokes) {
    drawStroke(context, points);
  }
}

function resizeCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  const context = canvas.getContext("2d");
  context.setTransform(1, 0, 0, 1, 0, 0);
  context.scale(ratio, ratio);
}

export function exportSignatureBase64(canvas) {
  if (!canvas) {
    return null;
  }
  const dataUrl = canvas.toDataURL("image/png");
  return dataUrl.replace(/^data:image\/png;base64,/, "");
}

export default function SignaturePad({ onChange, disabled = false }) {
  const canvasRef = useRef(null);
  const strokesRef = useRef([]);
  const activeStrokeRef = useRef(null);
  const drawingRef = useRef(false);
  const [isEmpty, setIsEmpty] = useState(true);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return undefined;
    }

    resizeCanvas(canvas);
    redrawCanvas(canvas, strokesRef.current);

    function handleResize() {
      resizeCanvas(canvas);
      redrawCanvas(canvas, strokesRef.current);
    }

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  function notifyChange(strokes) {
    const empty = totalStrokeLength(strokes) < MIN_STROKE_LENGTH;
    setIsEmpty(empty);
    if (empty) {
      onChange?.(null);
      return;
    }
    onChange?.(exportSignatureBase64(canvasRef.current));
  }

  function redraw() {
    redrawCanvas(canvasRef.current, strokesRef.current);
  }

  function handlePointerDown(event) {
    if (disabled) {
      return;
    }
    event.preventDefault();
    const canvas = canvasRef.current;
    canvas.setPointerCapture(event.pointerId);
    drawingRef.current = true;
    const point = getPoint(event, canvas);
    activeStrokeRef.current = [point];
    redraw();
  }

  function handlePointerMove(event) {
    if (!drawingRef.current || disabled) {
      return;
    }
    event.preventDefault();
    const canvas = canvasRef.current;
    const point = getPoint(event, canvas);
    activeStrokeRef.current.push(point);
    redraw();
    drawStroke(canvas.getContext("2d"), activeStrokeRef.current);
  }

  function finishStroke(event) {
    if (!drawingRef.current) {
      return;
    }
    if (event?.pointerId !== undefined && canvasRef.current?.hasPointerCapture(event.pointerId)) {
      canvasRef.current.releasePointerCapture(event.pointerId);
    }
    drawingRef.current = false;
    if (activeStrokeRef.current?.length) {
      strokesRef.current = [...strokesRef.current, activeStrokeRef.current];
      activeStrokeRef.current = null;
      redraw();
      notifyChange(strokesRef.current);
    }
  }

  function handleClear() {
    strokesRef.current = [];
    activeStrokeRef.current = null;
    drawingRef.current = false;
    redraw();
    notifyChange([]);
  }

  return (
    <div className="signature-pad">
      <canvas
        ref={canvasRef}
        className="signature-canvas"
        aria-label="Pole podpisu"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishStroke}
        onPointerCancel={finishStroke}
        onPointerLeave={finishStroke}
      />
      <div className="signature-actions">
        <button type="button" className="secondary-button" onClick={handleClear} disabled={disabled}>
          Wyczyść podpis
        </button>
      </div>
    </div>
  );
}
