import React, { useState, useMemo, memo } from 'react';
import { Copy, Check, FunctionSquare } from 'lucide-react';

// Common LaTeX Greek letters mapping
const GREEK_MAP = {
  alpha: 'α',
  beta: 'β',
  gamma: 'γ',
  Gamma: 'Γ',
  delta: 'δ',
  Delta: 'Δ',
  epsilon: 'ε',
  varepsilon: 'ε',
  zeta: 'ζ',
  eta: 'η',
  theta: 'θ',
  Theta: 'Θ',
  iota: 'ι',
  kappa: 'κ',
  lambda: 'λ',
  Lambda: 'Λ',
  mu: 'μ',
  nu: 'ν',
  xi: 'ξ',
  Xi: 'Ξ',
  pi: 'π',
  Pi: 'Π',
  rho: 'ρ',
  sigma: 'σ',
  Sigma: 'Σ',
  tau: 'τ',
  upsilon: 'υ',
  phi: 'φ',
  Phi: 'Φ',
  chi: 'χ',
  psi: 'ψ',
  Psi: 'Ψ',
  omega: 'ω',
  Omega: 'Ω',
};

// Common LaTeX Math Symbols & Operators mapping
const SYMBOLS_MAP = {
  sum: '∑',
  prod: '∏',
  int: '∫',
  oint: '∮',
  approx: '≈',
  sim: '∼',
  neq: '≠',
  ne: '≠',
  le: '≤',
  leq: '≤',
  ge: '≥',
  geq: '≥',
  times: '×',
  div: '÷',
  pm: '±',
  mp: '∓',
  cdot: '·',
  cdots: '⋯',
  ldots: '…',
  vdots: '⋮',
  ddots: '⋱',
  infty: '∞',
  in: '∈',
  notin: '∉',
  subset: '⊂',
  subseteq: '⊆',
  cup: '∪',
  cap: '∩',
  forall: '∀',
  exists: '∃',
  nabla: '∇',
  partial: '∂',
  to: '→',
  rightarrow: '→',
  leftarrow: '←',
  Rightarrow: '⇒',
  Leftarrow: '⇐',
  Leftrightarrow: '⇔',
  iff: '⇔',
  quad: '  ',
  qquad: '    ',
};

// Math function names that should be upright (not italic)
const MATH_FUNCS = new Set([
  'sin',
  'cos',
  'tan',
  'arcsin',
  'arccos',
  'arctan',
  'sinh',
  'cosh',
  'tanh',
  'log',
  'ln',
  'exp',
  'max',
  'min',
  'lim',
  'det',
  'arg',
  'deg',
  'dim',
  'gcd',
  'hom',
  'ker',
  'sec',
  'csc',
  'cot',
]);

/**
 * Tokenizes and parses LaTeX math tokens into React DOM elements.
 * Handles:
 * - \frac{num}{denom}
 * - \sqrt{expr}
 * - Subscripts _x, _{expr}
 * - Superscripts ^x, ^{expr}
 * - Greek symbols (\alpha, \beta, \sigma, etc.)
 * - Functions (\sin, \cos, \log, etc.)
 * - Upright text (\text{...}, \mathrm{...})
 */
function parseMathToNodes(inputStr) {
  if (!inputStr) return null;
  let str = inputStr.trim();

  // Strip enclosing \left and \right
  str = str.replace(/\\left\s*([(\[{|])/g, '$1').replace(/\\right\s*([)\]}|])/g, '$1');

  const nodes = [];
  let i = 0;
  let keyIndex = 0;

  function nextKey() {
    return `m_${keyIndex++}`;
  }

  while (i < str.length) {
    // 1. Fractions: \frac{num}{denom} or \dfrac{num}{denom}
    const fracMatch = /^\\(d?frac)\s*\{/i.exec(str.slice(i));
    if (fracMatch) {
      i += fracMatch[0].length;
      const numContent = extractBracedContent(str, i);
      i += numContent.length + 1; // +1 for closing brace
      while (str[i] && str[i] !== '{') i++;
      if (str[i] === '{') {
        i++;
        const denomContent = extractBracedContent(str, i);
        i += denomContent.length + 1;
        nodes.push(
          <span key={nextKey()} className="math-frac">
            <span className="math-num">{parseMathToNodes(numContent)}</span>
            <span className="math-denom">{parseMathToNodes(denomContent)}</span>
          </span>
        );
        continue;
      }
    }

    // 2. Square Root: \sqrt{content} or \sqrt[n]{content}
    const sqrtMatch = /^\\sqrt(?:\[([^\]]+)\])?\s*\{/i.exec(str.slice(i));
    if (sqrtMatch) {
      const rootIndex = sqrtMatch[1];
      i += sqrtMatch[0].length;
      const sqrtContent = extractBracedContent(str, i);
      i += sqrtContent.length + 1;
      nodes.push(
        <span key={nextKey()} className="math-sqrt">
          <span className="math-radical">
            {rootIndex ? <sup>{rootIndex}</sup> : null}√
          </span>
          <span className="math-radicand">{parseMathToNodes(sqrtContent)}</span>
        </span>
      );
      continue;
    }

    // 3. Upright Text: \text{...} or \mathrm{...}
    const textMatch = /^\\(text|mathrm)\s*\{/i.exec(str.slice(i));
    if (textMatch) {
      i += textMatch[0].length;
      const innerText = extractBracedContent(str, i);
      i += innerText.length + 1;
      nodes.push(
        <span key={nextKey()} className="math-text-upright">
          {innerText}
        </span>
      );
      continue;
    }

    // 4. LaTeX Command / Macro (\command)
    if (str[i] === '\\') {
      const cmdMatch = /^\\([a-zA-Z]+|[,;!])/i.exec(str.slice(i));
      if (cmdMatch) {
        const cmd = cmdMatch[1];
        i += cmdMatch[0].length;

        if (MATH_FUNCS.has(cmd)) {
          nodes.push(
            <span key={nextKey()} className="math-func">
              {cmd}
            </span>
          );
        } else if (GREEK_MAP[cmd]) {
          nodes.push(
            <span key={nextKey()} className="math-symbol math-greek">
              {GREEK_MAP[cmd]}
            </span>
          );
        } else if (SYMBOLS_MAP[cmd]) {
          nodes.push(
            <span key={nextKey()} className="math-symbol math-operator">
              {SYMBOLS_MAP[cmd]}
            </span>
          );
        } else {
          // Unknown command, output as text
          nodes.push(<span key={nextKey()}>{cmd}</span>);
        }
        continue;
      } else {
        i++; // skip dangling backslash
        continue;
      }
    }

    // 5. Subscript _
    if (str[i] === '_') {
      i++;
      let subContent = '';
      if (str[i] === '{') {
        i++;
        subContent = extractBracedContent(str, i);
        i += subContent.length + 1;
      } else if (str[i]) {
        subContent = str[i];
        i++;
      }
      nodes.push(
        <sub key={nextKey()} className="math-sub">
          {parseMathToNodes(subContent)}
        </sub>
      );
      continue;
    }

    // 6. Superscript ^
    if (str[i] === '^') {
      i++;
      let supContent = '';
      if (str[i] === '{') {
        i++;
        supContent = extractBracedContent(str, i);
        i += supContent.length + 1;
      } else if (str[i]) {
        supContent = str[i];
        i++;
      }
      nodes.push(
        <sup key={nextKey()} className="math-sup">
          {parseMathToNodes(supContent)}
        </sup>
      );
      continue;
    }

    // 7. Regular characters, operators, letters
    const char = str[i];
    if (/[a-zA-Z]/.test(char)) {
      nodes.push(
        <span key={nextKey()} className="math-var">
          {char}
        </span>
      );
    } else if (/[0-9]/.test(char)) {
      nodes.push(
        <span key={nextKey()} className="math-num-literal">
          {char}
        </span>
      );
    } else if (char === ' ') {
      nodes.push(<span key={nextKey()}> </span>);
    } else if (char === '*' || char === '•') {
      nodes.push(
        <span key={nextKey()} className="math-op">
          ·
        </span>
      );
    } else {
      nodes.push(
        <span key={nextKey()} className="math-op">
          {char}
        </span>
      );
    }
    i++;
  }

  return nodes;
}

/**
 * Extracts content inside matching curly braces {...}
 */
function extractBracedContent(str, startIndex) {
  let depth = 1;
  let j = startIndex;
  while (j < str.length && depth > 0) {
    if (str[j] === '{') depth++;
    else if (str[j] === '}') depth--;
    if (depth === 0) break;
    j++;
  }
  return str.slice(startIndex, j);
}

/**
 * MathFormula Component
 * Renders mathematical expressions cleanly with LaTeX typography.
 * Supports inline `$d_{model}$` and block `$$...$$` with copy button.
 */
function MathFormula({ formula, isBlock = false }) {
  const [copied, setCopied] = useState(false);
  const rawLatex = (formula || '').trim();

  const renderedContent = useMemo(() => {
    return parseMathToNodes(rawLatex);
  }, [rawLatex]);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(rawLatex);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  if (!rawLatex) return null;

  if (isBlock) {
    return (
      <div className="md-block-math" role="region" aria-label={`Formula: ${rawLatex}`}>
        <div className="md-block-math-inner">
          <div className="math-formula-body">{renderedContent}</div>
          <button
            type="button"
            className="md-math-copy-btn"
            onClick={onCopy}
            title={copied ? 'Copied LaTeX formula' : 'Copy LaTeX source'}
            aria-label={copied ? 'Copied formula' : 'Copy formula'}
          >
            {copied ? <Check size={12} color="#22c55e" /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'LaTeX'}</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <span className="md-inline-math" title={`$${rawLatex}$`}>
      {renderedContent}
    </span>
  );
}

export default memo(MathFormula);
