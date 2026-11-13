import React, { useState, useCallback, useMemo, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Copy,
  Check,
  FileCode,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Info,
  Lightbulb,
  AlertTriangle,
  AlertCircle,
  ShieldAlert,
  Terminal,
  Brain,
  WrapText,
} from 'lucide-react';

import Prism from 'prismjs';
import 'prismjs/components/prism-javascript.js';
import 'prismjs/components/prism-typescript.js';
import 'prismjs/components/prism-python.js';
import 'prismjs/components/prism-c.js';
import 'prismjs/components/prism-cpp.js';
import 'prismjs/components/prism-arduino.js';
import 'prismjs/components/prism-json.js';
import 'prismjs/components/prism-bash.js';
import 'prismjs/components/prism-sql.js';
import 'prismjs/components/prism-markup.js';
import 'prismjs/components/prism-css.js';
import 'prismjs/components/prism-yaml.js';
import 'prismjs/components/prism-markdown.js';
import 'prismjs/components/prism-rust.js';
import 'prismjs/components/prism-go.js';
import 'prismjs/components/prism-java.js';
import 'prismjs/components/prism-docker.js';
import 'prismjs/components/prism-diff.js';

import MathFormula from './MathFormula';

// Language aliases map
const LANG_MAP = {
  js: 'javascript',
  jsx: 'javascript',
  ts: 'typescript',
  tsx: 'typescript',
  py: 'python',
  python3: 'python',
  sh: 'bash',
  shell: 'bash',
  zsh: 'bash',
  c: 'c',
  cpp: 'cpp',
  'c++': 'cpp',
  cplusplus: 'cpp',
  arduino: 'arduino',
  ino: 'arduino',
  json: 'json',
  html: 'markup',
  xml: 'markup',
  svg: 'markup',
  css: 'css',
  sql: 'sql',
  yaml: 'yaml',
  yml: 'yaml',
  md: 'markdown',
  markdown: 'markdown',
  rust: 'rust',
  rs: 'rust',
  go: 'go',
  golang: 'go',
  java: 'java',
  docker: 'docker',
  dockerfile: 'docker',
  diff: 'diff',
};

const LANG_DISPLAY_NAMES = {
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  python: 'Python',
  arduino: 'Arduino',
  cpp: 'C++',
  c: 'C',
  json: 'JSON',
  bash: 'Bash / Shell',
  sql: 'SQL',
  markup: 'HTML / XML',
  css: 'CSS',
  yaml: 'YAML',
  markdown: 'Markdown',
  rust: 'Rust',
  go: 'Go',
  java: 'Java',
  docker: 'Dockerfile',
  diff: 'Diff',
};

// Callout alert types configuration
const CALLOUT_CONFIGS = {
  note: {
    label: 'Note',
    color: '#3b82f6',
    bg: 'rgba(59, 130, 246, 0.08)',
    border: '#3b82f6',
    icon: Info,
  },
  tip: {
    label: 'Tip',
    color: '#10b981',
    bg: 'rgba(16, 185, 129, 0.08)',
    border: '#10b981',
    icon: Lightbulb,
  },
  important: {
    label: 'Important',
    color: '#8b5cf6',
    bg: 'rgba(139, 92, 246, 0.08)',
    border: '#8b5cf6',
    icon: AlertCircle,
  },
  warning: {
    label: 'Warning',
    color: '#f59e0b',
    bg: 'rgba(245, 158, 11, 0.08)',
    border: '#f59e0b',
    icon: AlertTriangle,
  },
  caution: {
    label: 'Caution',
    color: '#ef4444',
    bg: 'rgba(239, 68, 68, 0.08)',
    border: '#ef4444',
    icon: ShieldAlert,
  },
};

/**
 * Replaces LaTeX math patterns ($...$ and $$...$$) with MathFormula components
 */
function renderWithMath(children) {
  if (typeof children === 'string') {
    if (!children.includes('$')) return children;

    const parts = [];
    let lastIdx = 0;
    // Match block math $$...$$ first, then inline math $...$
    const mathRegex = /(\$\$[\s\S]+?\$\$|(?<!\\|\d)\$(?!\s)[^\$\n]+?(?<!\s)\$(?!\d))/g;
    let match;
    let k = 0;

    while ((match = mathRegex.exec(children)) !== null) {
      if (match.index > lastIdx) {
        parts.push(children.slice(lastIdx, match.index));
      }
      const fullMatch = match[0];
      if (fullMatch.startsWith('$$') && fullMatch.endsWith('$$')) {
        const inner = fullMatch.slice(2, -2).trim();
        parts.push(<MathFormula key={`bm_${k++}`} formula={inner} isBlock />);
      } else {
        const inner = fullMatch.slice(1, -1).trim();
        parts.push(<MathFormula key={`im_${k++}`} formula={inner} isBlock={false} />);
      }
      lastIdx = match.index + fullMatch.length;
    }
    if (lastIdx < children.length) {
      parts.push(children.slice(lastIdx));
    }
    return parts.length > 0 ? parts : children;
  }

  if (Array.isArray(children)) {
    return React.Children.map(children, (c) => (React.isValidElement(c) ? c : renderWithMath(c)));
  }

  return children;
}

/**
 * Collapsible Thinking Process component for reasoning models (<think>...</think>)
 */
const ThoughtBlock = memo(function ThoughtBlock({ thoughtText, isThinking = false }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="md-thought-block" style={{ margin: '10px 0', borderRadius: '8px', overflow: 'hidden' }}>
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 12px',
          background: 'rgba(234, 88, 12, 0.06)',
          border: '1px solid rgba(234, 88, 12, 0.2)',
          borderRadius: '8px',
          color: '#a3a3a3',
          cursor: 'pointer',
          fontSize: '12px',
          fontWeight: 500,
          width: '100%',
          textAlign: 'left',
          transition: 'all 0.15s ease',
        }}
        aria-expanded={expanded}
      >
        <Brain size={14} color="#ea580c" />
        <span style={{ color: '#d4d4d4' }}>{isThinking ? 'Thinking process in progress...' : 'Thought process & reasoning'}</span>
        {expanded ? <ChevronDown size={14} style={{ marginLeft: 'auto' }} /> : <ChevronRight size={14} style={{ marginLeft: 'auto' }} />}
      </button>

      {expanded && (
        <div
          style={{
            padding: '10px 14px',
            marginTop: '4px',
            background: 'rgba(0, 0, 0, 0.25)',
            border: '1px solid #262626',
            borderRadius: '8px',
            fontSize: '12px',
            lineHeight: 1.6,
            color: '#8e8e8e',
            fontStyle: 'italic',
            whiteSpace: 'pre-wrap',
            maxHeight: '260px',
            overflowY: 'auto',
          }}
        >
          {thoughtText}
        </div>
      )}
    </div>
  );
});

/**
 * Enhanced CodeBlock with Copy button, Wrap toggle, and Language Badge
 */
const CodeBlock = memo(function CodeBlock({ language = '', code = '' }) {
  const [copied, setCopied] = useState(false);
  const [wrapLines, setWrapLines] = useState(false);

  const rawLang = (language || '').toLowerCase().trim();
  const canonicalLang = LANG_MAP[rawLang] || rawLang;
  const displayName = LANG_DISPLAY_NAMES[canonicalLang] || rawLang || 'Code';

  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  }, [code]);

  // Syntax highlighting via Prism
  const highlightedHtml = useMemo(() => {
    if (canonicalLang && Prism.languages[canonicalLang]) {
      try {
        return Prism.highlight(code, Prism.languages[canonicalLang], canonicalLang);
      } catch {
        return null;
      }
    }
    return null;
  }, [code, canonicalLang]);

  const lineCount = useMemo(() => (code ? code.split('\n').length : 1), [code]);

  return (
    <div className="md-code-block" data-language={canonicalLang}>
      <div className="md-code-header">
        <span className="md-code-lang">
          {canonicalLang === 'bash' ? (
            <Terminal size={13} className="md-code-icon" color="#ea580c" aria-hidden="true" />
          ) : (
            <FileCode size={13} className="md-code-icon" aria-hidden="true" />
          )}
          <span>{displayName}</span>
          {lineCount > 1 && (
            <span style={{ opacity: 0.6, fontWeight: 400, fontSize: '11px', marginLeft: '6px' }}>
              ({lineCount} lines)
            </span>
          )}
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {lineCount > 1 && (
            <button
              type="button"
              className="md-code-copy-btn"
              onClick={() => setWrapLines((w) => !w)}
              title={wrapLines ? 'Disable line wrap' : 'Enable line wrap'}
              aria-label="Toggle line wrap"
              style={{ opacity: wrapLines ? 1 : 0.7 }}
            >
              <WrapText size={12} aria-hidden="true" />
              <span>Wrap</span>
            </button>
          )}

          <button
            type="button"
            className="md-code-copy-btn"
            onClick={onCopy}
            aria-label={copied ? 'Copied code to clipboard' : 'Copy code'}
            title="Copy code"
          >
            {copied ? (
              <>
                <Check size={13} className="text-success" aria-hidden="true" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy size={13} aria-hidden="true" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      <pre className="md-code-pre" style={{ whiteSpace: wrapLines ? 'pre-wrap' : 'pre', wordBreak: wrapLines ? 'break-word' : 'normal' }}>
        {highlightedHtml ? (
          <code
            className={`language-${canonicalLang}`}
            dangerouslySetInnerHTML={{ __html: highlightedHtml }}
          />
        ) : (
          <code>{code}</code>
        )}
      </pre>
    </div>
  );
});

/**
 * Pre-processes LLM output to:
 * 1. Extract <think> or <thought> reasoning blocks.
 * 2. Auto-close dangling triple backtick code fences caused by streaming.
 */
function preprocessLlmMarkdown(rawText) {
  if (!rawText || typeof rawText !== 'string') return { thoughts: [], cleanText: '' };

  let text = rawText;
  const thoughts = [];

  // Match complete <think>...</think> or <thought>...</thought>
  text = text.replace(/<(think|thought)>([\s\S]*?)<\/\1>/gi, (_, tag, content) => {
    thoughts.push({ content: content.trim(), isThinking: false });
    return '';
  });

  // Match unclosed <think>... at the end during streaming
  const openThinkMatch = /<(think|thought)>([\s\S]*?)$/i.exec(text);
  if (openThinkMatch) {
    thoughts.push({ content: openThinkMatch[2].trim(), isThinking: true });
    text = text.slice(0, openThinkMatch.index);
  }

  // Auto-close dangling triple backticks from streaming LLMs
  const backtickMatches = text.match(/```/g);
  if (backtickMatches && backtickMatches.length % 2 !== 0) {
    text = text + '\n```';
  }

  return { thoughts, cleanText: text.trim() };
}

/**
 * Markdown
 * State-of-the-art markdown parser and renderer for LLM output.
 * Features:
 * - Mathematical formula parsing: $d_{model}$, Sine/Cosine, $\frac{a}{b}$, matrices
 * - Auto-closing streaming code blocks
 * - Reasoning model thought disclosure (<think>...</think>)
 * - GitHub/Claude callout admonitions ([!NOTE], [!TIP], [!WARNING], [!CAUTION])
 * - Full Prism syntax highlighting across 18 languages
 * - GFM tables, task lists, and accessible links
 */
function Markdown({ children }) {
  if (!children) return null;

  const rawInput = typeof children === 'string' ? children : String(children || '');
  const { thoughts, cleanText } = useMemo(() => preprocessLlmMarkdown(rawInput), [rawInput]);

  return (
    <div className="md-container">
      {/* Reasoning / Thinking disclosures if present */}
      {thoughts.map((th, idx) => (
        <ThoughtBlock key={idx} thoughtText={th.content} isThinking={th.isThinking} />
      ))}

      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p({ children, ...props }) {
            return <p {...props}>{renderWithMath(children)}</p>;
          },
          li({ children, ...props }) {
            return <li {...props}>{renderWithMath(children)}</li>;
          },
          h1({ children, ...props }) {
            return <h1 {...props}>{renderWithMath(children)}</h1>;
          },
          h2({ children, ...props }) {
            return <h2 {...props}>{renderWithMath(children)}</h2>;
          },
          h3({ children, ...props }) {
            return <h3 {...props}>{renderWithMath(children)}</h3>;
          },
          h4({ children, ...props }) {
            return <h4 {...props}>{renderWithMath(children)}</h4>;
          },
          pre({ children }) {
            return <>{children}</>;
          },
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const codeString = String(children || '').replace(/\n$/, '');
            const isBlock = Boolean(match || codeString.includes('\n'));

            if (isBlock) {
              return <CodeBlock language={match ? match[1] : ''} code={codeString} />;
            }
            return (
              <code className="md-inline-code" {...props}>
                {children}
              </code>
            );
          },
          table({ children, ...props }) {
            return (
              <div className="md-table-wrap">
                <table className="md-table" {...props}>
                  {children}
                </table>
              </div>
            );
          },
          th({ children, ...props }) {
            return <th {...props}>{renderWithMath(children)}</th>;
          },
          td({ children, ...props }) {
            return <td {...props}>{renderWithMath(children)}</td>;
          },
          a({ href, children, ...props }) {
            const isExternal = href && (href.startsWith('http://') || href.startsWith('https://'));
            return (
              <a
                href={href}
                className="md-link"
                target={isExternal ? '_blank' : undefined}
                rel={isExternal ? 'noopener noreferrer' : undefined}
                {...props}
              >
                <span>{renderWithMath(children)}</span>
                {isExternal && <ExternalLink size={11} className="md-link-ext" aria-hidden="true" />}
              </a>
            );
          },
          blockquote({ children, ...props }) {
            // Check for GitHub / Claude style callout banners [!NOTE], [!TIP], etc.
            let firstText = '';
            React.Children.forEach(children, (child) => {
              if (typeof child === 'string') firstText += child;
              else if (child?.props?.children && typeof child.props.children === 'string') {
                firstText += child.props.children;
              }
            });

            const calloutMatch = /^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)/i.exec(firstText.trim());
            if (calloutMatch) {
              const calloutKey = calloutMatch[1].toLowerCase();
              const config = CALLOUT_CONFIGS[calloutKey] || CALLOUT_CONFIGS.note;
              const Icon = config.icon;
              const remainingText = calloutMatch[2];

              return (
                <div
                  className={`md-callout md-callout-${calloutKey}`}
                  style={{
                    margin: '12px 0',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    background: config.bg,
                    borderLeft: `3.5px solid ${config.border}`,
                    color: 'var(--text)',
                  }}
                  role="note"
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: config.color, marginBottom: '4px' }}>
                    <Icon size={14} />
                    <span>{config.label}</span>
                  </div>
                  <div style={{ fontSize: '0.94rem', lineHeight: 1.55 }}>
                    {remainingText ? renderWithMath(remainingText) : renderWithMath(children)}
                  </div>
                </div>
              );
            }

            return (
              <blockquote className="md-blockquote" {...props}>
                {renderWithMath(children)}
              </blockquote>
            );
          },
          ul({ children, className, ...props }) {
            const isTaskList = className && className.includes('contains-task-list');
            return (
              <ul className={`md-ul ${isTaskList ? 'md-task-list' : ''}`} {...props}>
                {children}
              </ul>
            );
          },
          ol({ children, ...props }) {
            return (
              <ol className="md-ol" {...props}>
                {children}
              </ol>
            );
          },
          hr({ ...props }) {
            return <hr className="md-hr" {...props} />;
          },
        }}
      >
        {cleanText}
      </ReactMarkdown>
    </div>
  );
}

export default memo(Markdown);
