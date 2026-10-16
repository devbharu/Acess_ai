import { memo, useMemo } from 'react';

export const BarList = memo(function BarList({ items, max = 100, unit = '%', label }) {
  return (
    <div className="bars" role="list" aria-label={label}>
      {items.map((it) => (
        <div className="bar-row" role="listitem" key={it.label}>
          <span>{it.label}</span>
          <div className="bar-track" aria-hidden><div className="bar-fill" style={{ width: `${Math.min(100, (it.value / max) * 100)}%` }} /></div>
          <span className="bar-val">{it.value}{unit}</span>
        </div>
      ))}
    </div>
  );
});

const W = 520, H = 220, P = { l: 36, r: 12, t: 12, b: 26 };

export const LineChart = memo(function LineChart({ series, labels, unit = '', label }) {
  const geo = useMemo(() => {
    const all = series.flatMap((s) => s.values);
    const lo = Math.min(...all), hi = Math.max(...all);
    const pad = (hi - lo || 1) * 0.15;
    const y0 = Math.max(0, lo - pad), y1 = hi + pad;
    const x = (i) => P.l + (i / Math.max(1, labels.length - 1)) * (W - P.l - P.r);
    const y = (v) => H - P.b - ((v - y0) / (y1 - y0)) * (H - P.t - P.b);
    const ticks = [0, 1, 2, 3].map((k) => y0 + ((y1 - y0) * k) / 3);
    return { x, y, ticks };
  }, [series, labels]);

  return (
    <svg className="line-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
      {geo.ticks.map((t) => (
        <g key={t}>
          <line x1={P.l} x2={W - P.r} y1={geo.y(t)} y2={geo.y(t)} stroke="var(--line)" strokeDasharray="3 4" />
          <text x={P.l - 6} y={geo.y(t) + 3} textAnchor="end">{Math.round(t * 10) / 10}{unit}</text>
        </g>
      ))}
      {labels.map((l, i) => (labels.length <= 8 || i % Math.ceil(labels.length / 8) === 0) && (
        <text key={l + i} x={geo.x(i)} y={H - 6} textAnchor="middle">{l}</text>
      ))}
      {series.map((s) => (
        <g key={s.name}>
          <polyline fill="none" stroke={s.color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round"
            points={s.values.map((v, i) => `${geo.x(i)},${geo.y(v)}`).join(' ')} />
          {s.values.map((v, i) => <circle key={i} cx={geo.x(i)} cy={geo.y(v)} r="3.5" fill="var(--surface)" stroke={s.color} strokeWidth="2" />)}
        </g>
      ))}
    </svg>
  );
});
