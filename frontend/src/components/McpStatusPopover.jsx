import { useState, useEffect, useRef } from 'react';
import { Cpu, X, Search, Terminal, Radio, CheckCircle2, ChevronRight, ChevronDown } from 'lucide-react';
import { api } from '../api/client';

export default function McpStatusPopover({ onClose, alignRight = true }) {
  const [status, setStatus] = useState(null);
  const [tools, setTools] = useState([]);
  const [search, setSearch] = useState('');
  const [expandedTool, setExpandedTool] = useState(null);
  const [loading, setLoading] = useState(true);
  const popoverRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    Promise.all([api.getMcpStatus(), api.getMcpTools()])
      .then(([statusRes, toolsRes]) => {
        if (!mounted) return;
        setStatus(statusRes);
        setTools(toolsRes.tools || []);
        setLoading(false);
      })
      .catch((err) => {
        if (!mounted) return;
        console.error('Failed to load MCP status:', err);
        setLoading(false);
      });

    return () => { mounted = false; };
  }, []);

  // Handle escape & outside click
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose();
    }
    function handleClickOutside(e) {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        onClose();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);

  const filteredTools = tools.filter((t) => {
    const q = search.toLowerCase();
    return (
      t.name.toLowerCase().includes(q) ||
      (t.description && t.description.toLowerCase().includes(q)) ||
      (t.category && t.category.toLowerCase().includes(q))
    );
  });

  // Group tools by category
  const categories = ['Document', 'Vision', 'Analysis', 'Audio', 'Catalog'];
  const grouped = categories.reduce((acc, cat) => {
    acc[cat] = filteredTools.filter((t) => t.category === cat);
    return acc;
  }, {});

  return (
    <div
      ref={popoverRef}
      className={`lookup-popover mcp-popover ${alignRight ? 'align-right' : ''}`}
      role="dialog"
      aria-label="Model Context Protocol Server & Tools"
      style={{
        position: 'absolute',
        top: 'calc(100% + 8px)',
        right: alignRight ? 0 : 'auto',
        width: '380px',
        maxHeight: '480px',
        background: '#141414',
        border: '1px solid #282828',
        borderRadius: '12px',
        boxShadow: '0 12px 32px rgba(0,0,0,0.4)',
        zIndex: 100,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        color: '#e5e5e5',
        fontSize: '13px',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderBottom: '1px solid #222',
          background: '#181818',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Cpu size={16} color="#ea580c" />
          <span style={{ fontWeight: 600, fontSize: '14px' }}>Model Context Protocol</span>
        </div>
        <button
          type="button"
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#888',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '4px',
          }}
          aria-label="Close MCP status"
        >
          <X size={15} />
        </button>
      </div>

      {/* Status banner */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #222', background: '#111' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                display: 'inline-block',
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: status?.status === 'active' ? '#22c55e' : '#eab308',
                boxShadow: status?.status === 'active' ? '0 0 8px rgba(34,197,94,0.6)' : 'none',
              }}
            />
            <span style={{ fontWeight: 500, color: '#f5f5f5' }}>
              {status ? `${status.server} v${status.version}` : 'Connecting...'}
            </span>
          </div>
          <span style={{ fontSize: '11px', color: '#888', background: '#222', padding: '2px 6px', borderRadius: '4px' }}>
            Spec {status?.protocol_version || '2024-11-05'}
          </span>
        </div>

        {/* Transports */}
        <div style={{ display: 'flex', gap: '8px', fontSize: '11px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#a3a3a3' }}>
            <Terminal size={12} color="#ea580c" />
            <span>stdio (Claude Desktop)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#a3a3a3' }}>
            <Radio size={12} color="#3b82f6" />
            <span>SSE (/api/mcp/sse)</span>
          </div>
        </div>
      </div>

      {/* Search Input */}
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #222' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: '#1a1a1a',
            padding: '6px 10px',
            borderRadius: '6px',
            border: '1px solid #282828',
          }}
        >
          <Search size={13} color="#666" />
          <input
            type="text"
            placeholder="Search 18 MCP tools..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#e5e5e5',
              fontSize: '12px',
              width: '100%',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Tools List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
        {loading ? (
          <div style={{ padding: '24px', textAlign: 'center', color: '#666' }}>Loading MCP tools...</div>
        ) : filteredTools.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: '#666' }}>No matching tools found.</div>
        ) : (
          categories.map((cat) => {
            const catTools = grouped[cat] || [];
            if (catTools.length === 0) return null;

            return (
              <div key={cat} style={{ marginBottom: '12px' }}>
                <div
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    color: '#ea580c',
                    letterSpacing: '0.5px',
                    padding: '4px 6px',
                  }}
                >
                  {cat} Tools ({catTools.length})
                </div>

                {catTools.map((t) => {
                  const isExp = expandedTool === t.name;
                  const reqProps = t.inputSchema?.required || [];

                  return (
                    <div
                      key={t.name}
                      style={{
                        background: isExp ? '#1c1c1c' : '#161616',
                        border: '1px solid',
                        borderColor: isExp ? '#ea580c33' : '#222',
                        borderRadius: '6px',
                        marginBottom: '6px',
                        overflow: 'hidden',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => setExpandedTool(isExp ? null : t.name)}
                        style={{
                          width: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '8px 10px',
                          background: 'transparent',
                          border: 'none',
                          color: '#f5f5f5',
                          cursor: 'pointer',
                          textAlign: 'left',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                          <CheckCircle2 size={12} color="#22c55e" style={{ flexShrink: 0 }} />
                          <code style={{ fontSize: '12px', color: '#f97316', fontFamily: 'monospace' }}>
                            {t.name}
                          </code>
                        </div>
                        {isExp ? <ChevronDown size={14} color="#888" /> : <ChevronRight size={14} color="#888" />}
                      </button>

                      {isExp && (
                        <div
                          style={{
                            padding: '8px 10px 10px 10px',
                            borderTop: '1px solid #262626',
                            fontSize: '12px',
                            color: '#a3a3a3',
                            background: '#121212',
                          }}
                        >
                          <p style={{ margin: '0 0 6px 0', lineHeight: 1.4 }}>{t.description}</p>
                          {reqProps.length > 0 && (
                            <div style={{ fontSize: '11px', color: '#737373', marginTop: '4px' }}>
                              <strong style={{ color: '#a3a3a3' }}>Required: </strong>
                              {reqProps.map((p) => (
                                <span
                                  key={p}
                                  style={{
                                    display: 'inline-block',
                                    background: '#262626',
                                    color: '#f5f5f5',
                                    padding: '1px 5px',
                                    borderRadius: '3px',
                                    marginRight: '4px',
                                  }}
                                >
                                  {p}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '8px 16px',
          borderTop: '1px solid #222',
          background: '#181818',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '11px',
          color: '#737373',
        }}
      >
        <span>18 Tools · 4 Resources · 3 Prompts</span>
        <span style={{ color: '#ea580c' }}>AccessAI MCP Ready</span>
      </div>
    </div>
  );
}
