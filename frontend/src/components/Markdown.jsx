import React, { useState, useCallback, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, FileCode, ExternalLink } from 'lucide-react';

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
  css: 'css',
  sql: 'sql',
  yaml: 'yaml',
  yml: 'yaml',
  md: 'markdown',
  markdown: 'markdown',
};

const LANG_DISPLAY_NAMES = {
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  python: 'Python',
  arduino: 'Arduino',
  cpp: 'C++',
  c: 'C',
  json: 'JSON',
  bash: 'Bash',
  sql: 'SQL',
  markup: 'HTML',
  css: 'CSS',
  yaml: 'YAML',
  markdown: 'Markdown',
};

const CodeBlock = memo(function CodeBlock({ language = '', code = '' }) {
  const [copied, setCopied] = useState(false);

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
  let highlightedHtml = null;
  if (canonicalLang && Prism.languages[canonicalLang]) {
    try {
      highlightedHtml = Prism.highlight(code, Prism.languages[canonicalLang], canonicalLang);
    } catch {
      highlightedHtml = null;
    }
  }

  return (
    <div className="md-code-block" data-language={canonicalLang}>
      <div className="md-code-header">
        <span className="md-code-lang">
          <FileCode size={13} className="md-code-icon" aria-hidden="true" />
          <span>{displayName}</span>
        </span>
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
      <pre className="md-code-pre">
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

function Markdown({ children }) {
  if (!children) return null;

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
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
              <span>{children}</span>
              {isExternal && <ExternalLink size={11} className="md-link-ext" aria-hidden="true" />}
            </a>
          );
        },
        blockquote({ children, ...props }) {
          return (
            <blockquote className="md-blockquote" {...props}>
              {children}
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
      {children}
    </ReactMarkdown>
  );
}

export default memo(Markdown);
