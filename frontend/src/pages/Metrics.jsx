import { useCallback, useEffect, useState } from 'react';
import { BarChart3, Loader2, Play } from 'lucide-react';
import { api } from '../api/client';
import { BarList, LineChart } from '../components/Charts';

const Stat = ({ label, value, unit, note, accent }) => (
  <div className={`stat ${accent ? 'accent' : ''}`}>
    <span className="stat-label">{label}</span>
    <span className="stat-value">{value ?? '—'}{value != null && unit && <small>{unit}</small>}</span>
    {note && <span className="stat-note">{note}</span>}
  </div>
);

const SUITES = [
  ['all', 'Run full evaluation'],
  ['stt', 'Speech (WER)'],
  ['ocr', 'OCR (CER)'],
  ['qa', 'Answers & grounding'],
];

export default function Metrics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try { setData(await api.getMetrics()); setError(''); } catch (e) { setError(e.message); } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const run = async (suite) => {
    setRunning(suite);
    setError('');
    try { await api.runEvaluation(suite); await load(); } catch (e) { setError(e.message); } finally { setRunning(null); }
  };

  const s = data?.summary;
  const hasData = s && Object.values(s).some((v) => v != null);

  return (
    <div className="page">
      <div className="page-inner">
        <div className="page-head">
          <div>
            <h1>Evaluation</h1>
            <p>How well each part of the pipeline performs: speech recognition, OCR, retrieval, answer quality and speed.</p>
          </div>
          <div className="presets">
            {SUITES.map(([key, label]) => (
              <button key={key} type="button" className={`btn btn-sm ${key === 'all' ? 'btn-primary' : ''}`} disabled={!!running} onClick={() => run(key)}>
                {running === key ? <Loader2 size={15} className="spin" /> : <Play size={14} />} {label}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="error-text" role="alert">{error}</p>}

        {loading ? (
          <div className="stat-grid" aria-busy="true">{Array.from({ length: 6 }, (_, i) => <div key={i} className="skeleton" style={{ height: 118 }} />)}</div>
        ) : !hasData ? (
          <div className="empty-state">
            <BarChart3 size={40} aria-hidden />
            <h2>No evaluation results yet</h2>
            <p>Run the evaluation to measure word error rate, OCR accuracy, answer correctness, hallucination control and latency on your test sets.</p>
            <button type="button" className="btn btn-primary" disabled={!!running} onClick={() => run('all')}>
              {running ? <Loader2 size={16} className="spin" /> : <Play size={15} />} Run full evaluation
            </button>
          </div>
        ) : (
          <>
            <div className="stat-grid">
              <Stat accent label="Answer correctness" value={s.answer_correctness} unit="%" note="Judged against reference answers" />
              <Stat label="Word error rate" value={s.wer} unit="%" note="Speech recognition · lower is better" />
              <Stat label="OCR accuracy" value={s.ocr_accuracy} unit="%" note="1 − character error rate" />
              <Stat label="Faithfulness" value={s.faithfulness} unit="%" note="Answers supported by evidence" />
              <Stat label="Hallucination rate" value={s.hallucination_rate} unit="%" note="Unsupported claims · lower is better" />
              <Stat label="Retrieval hit@k" value={s.retrieval_hit} unit="%" note="Right passage in top-k" />
              <Stat label="Latency p50" value={s.latency_p50} unit="s" note="End to end, voice in to text out" />
              <Stat label="Latency p95" value={s.latency_p95} unit="s" />
            </div>

            <div className="chart-grid">
              {!!data.history?.length && (
                <section className="card chart-card" aria-labelledby="h-trend">
                  <h2 id="h-trend">Quality over runs</h2>
                  <LineChart label="Answer correctness and OCR accuracy across evaluation runs" unit="%" labels={data.history.map((h) => h.label)}
                    series={[
                      { name: 'Answer correctness', color: 'var(--accent)', values: data.history.map((h) => h.answer_correctness) },
                      { name: 'OCR accuracy', color: 'var(--text)', values: data.history.map((h) => h.ocr_accuracy) },
                    ]} />
                  <p className="hint">Orange: answer correctness · Dark: OCR accuracy</p>
                </section>
              )}
              {!!data.robustness?.length && (
                <section className="card chart-card" aria-labelledby="h-rob">
                  <h2 id="h-rob">Robustness tests</h2>
                  <BarList label="Answer correctness by test condition" items={data.robustness} />
                </section>
              )}
              {!!data.latency?.length && (
                <section className="card chart-card" aria-labelledby="h-lat">
                  <h2 id="h-lat">Latency by stage</h2>
                  <BarList label="Average seconds per pipeline stage" items={data.latency} unit="s" max={Math.max(...data.latency.map((l) => l.value)) * 1.15} />
                </section>
              )}
            </div>

            {!!data.runs?.length && (
              <section className="card" aria-labelledby="h-runs">
                <h2 id="h-runs" style={{ marginBottom: 14 }}>Recent runs</h2>
                <div className="table-wrap">
                  <table className="data">
                    <thead><tr><th>Date</th><th>Suite</th><th>Model</th><th>Samples</th><th>Score</th><th>Duration</th></tr></thead>
                    <tbody>
                      {data.runs.map((r) => (
                        <tr key={r.id}>
                          <td>{new Date(r.created_at).toLocaleString()}</td><td>{r.suite}</td><td>{r.model}</td>
                          <td className="num">{r.samples}</td><td className="num">{r.score}%</td><td className="num">{r.duration_s}s</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}
