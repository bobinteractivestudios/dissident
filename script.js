const canvas = document.getElementById("noise");
const ctx = canvas.getContext("2d");

function generateNoise() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const scale = window.devicePixelRatio || 1;

  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  ctx.setTransform(scale, 0, 0, scale, 0, 0);

  ctx.clearRect(0, 0, width, height);

  const density = 0.19;
  const cellSize = 7.5;
  const color = "rgb(73, 73, 73)";
  const count = Math.round((width * height) / (cellSize * cellSize) * density);

  ctx.lineJoin = "round";

  for (let i = 0; i < count; i++) {
    const x = Math.random() * width;
    const y = Math.random() * height;
    const base = Math.random() * cellSize * 0.3 + 1.2;
    const alpha = 0.35 + Math.random() * 0.25;

    ctx.fillStyle = color;
    ctx.globalAlpha = alpha;

    ctx.beginPath();
    const points = 4 + Math.floor(Math.random() * 2);
    for (let p = 0; p < points; p++) {
      const angle = (Math.PI * 2 * p) / points;
      const radius = base + (Math.random() - 0.5) * base * 0.6;
      const px = x + Math.cos(angle) * radius;
      const py = y + Math.sin(angle) * radius * (0.8 + Math.random() * 0.4);
      if (p === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fill();

    if (Math.random() < 0.45) {
      ctx.beginPath();
      const innerRadius = base * (0.3 + Math.random() * 0.2);
      ctx.arc(x + (Math.random() - 0.5) * base * 0.3, y + (Math.random() - 0.5) * base * 0.3, innerRadius, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  ctx.globalAlpha = 1;
}

generateNoise();
window.addEventListener("resize", generateNoise);