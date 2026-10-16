import { memo, useId } from 'react';

export const Slider = memo(function Slider({ label, hint, value, min, max, step, onChange, format }) {
  const id = useId();
  const fill = ((value - min) / (max - min)) * 100;
  return (
    <div className="slider">
      <div className="slider-head">
        <label htmlFor={id} className="label">{label}</label>
        <output htmlFor={id} className="slider-value">{format ? format(value) : value}</output>
      </div>
      <input
        id={id} type="range" min={min} max={max} step={step} value={value}
        style={{ '--fill': `${fill}%` }}
        aria-describedby={hint ? `${id}-h` : undefined}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      {hint && <p id={`${id}-h`} className="hint">{hint}</p>}
    </div>
  );
});

export const Toggle = memo(function Toggle({ label, hint, checked, onChange }) {
  const id = useId();
  return (
    <div className="toggle">
      <div className="toggle-text">
        <span id={`${id}-l`} className="label">{label}</span>
        {hint && <span className="hint">{hint}</span>}
      </div>
      <button type="button" role="switch" className="switch" aria-checked={checked} aria-labelledby={`${id}-l`} onClick={() => onChange(!checked)} />
    </div>
  );
});

export const Segmented = memo(function Segmented({ label, options, value, onChange }) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {options.map(([val, text]) => (
        <button key={val} type="button" role="radio" aria-checked={value === val} onClick={() => onChange(val)}>{text}</button>
      ))}
    </div>
  );
});

export const Field = ({ label, hint, children }) => {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children(id)}
      {hint && <p className="hint">{hint}</p>}
    </div>
  );
};
