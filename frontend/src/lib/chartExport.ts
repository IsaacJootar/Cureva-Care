// Export helpers for the chart kit (WS8): CSV for the underlying data, PNG for
// the rendered SVG. PNG inlines the design-system CSS variables the SVG uses so
// the exported image keeps its colours outside the document.

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function esc(v: string | number | null | undefined): string {
  const s = v == null ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function downloadCSV(
  filename: string,
  header: string[],
  rows: (string | number | null)[][],
) {
  const csv = [header.map(esc).join(","), ...rows.map((r) => r.map(esc).join(","))].join("\n");
  triggerDownload(
    new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }),
    filename.endsWith(".csv") ? filename : `${filename}.csv`,
  );
}

// CSS variables the chart SVGs reference — snapshotted into the export so colours
// survive outside the live document.
const CHART_VARS = [
  "--cv-series-1", "--cv-series-2", "--cv-series-3", "--cv-series-4",
  "--cv-accent-solid", "--cv-accent-soft", "--cv-text-primary",
  "--cv-text-secondary", "--cv-text-muted", "--cv-hairline",
  "--cv-card-bg", "--cv-danger-icon", "--cv-warning-icon", "--cv-success-icon",
];

export function svgToPng(svg: SVGSVGElement, filename: string, scale = 2) {
  try {
    const clone = svg.cloneNode(true) as SVGSVGElement;
    const cs = getComputedStyle(document.documentElement);
    const decls = CHART_VARS.map((v) => `${v}:${cs.getPropertyValue(v).trim()}`).join(";");
    const styleEl = document.createElementNS("http://www.w3.org/2000/svg", "style");
    styleEl.textContent = `:root{${decls}} text{font-family:'Segoe UI',system-ui,sans-serif}`;
    clone.insertBefore(styleEl, clone.firstChild);

    const vb = svg.viewBox.baseVal;
    const w = (vb && vb.width) || svg.clientWidth || 680;
    const h = (vb && vb.height) || svg.clientHeight || 260;
    clone.setAttribute("width", String(w));
    clone.setAttribute("height", String(h));

    const xml = new XMLSerializer().serializeToString(clone);
    const svg64 = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(xml)));
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = w * scale;
      canvas.height = h * scale;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.fillStyle = cs.getPropertyValue("--cv-card-bg").trim() || "#fff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        if (blob) triggerDownload(blob, filename.endsWith(".png") ? filename : `${filename}.png`);
      }, "image/png");
    };
    img.src = svg64;
  } catch {
    /* best-effort; CSV export is the reliable path */
  }
}
