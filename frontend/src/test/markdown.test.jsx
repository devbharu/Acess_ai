import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Markdown from '../components/Markdown';

describe('Markdown output parser', () => {
  it('renders headings and paragraphs', () => {
    const md = '### Arduino Push Button\n\nThis is an explanation of the circuit.';
    render(<Markdown>{md}</Markdown>);
    expect(screen.getByRole('heading', { level: 3, name: 'Arduino Push Button' })).toBeTruthy();
    expect(screen.getByText('This is an explanation of the circuit.')).toBeTruthy();
  });

  it('renders GFM tables correctly', () => {
    const md = `
| Component | Value | Pin |
| :--- | :--- | :--- |
| LED | Red 5mm | Pin 13 |
| Resistor | 220 Ohm | Pin 13 |
| Push Button | Tactile | Pin 2 |
`;
    render(<Markdown>{md}</Markdown>);
    expect(screen.getByRole('table')).toBeTruthy();
    expect(screen.getByRole('columnheader', { name: 'Component' })).toBeTruthy();
    expect(screen.getByRole('cell', { name: '220 Ohm' })).toBeTruthy();
  });

  it('renders syntax-highlighted code block with language badge and copy button', () => {
    const md = '```arduino\nconst int ledPin = 13;\nvoid setup() {\n  pinMode(ledPin, OUTPUT);\n}\n```';
    render(<Markdown>{md}</Markdown>);
    expect(screen.getByText('Arduino')).toBeTruthy();
    const copyBtn = screen.getByRole('button', { name: 'Copy code' });
    expect(copyBtn).toBeTruthy();

    const codeEl = document.querySelector('.md-code-pre code');
    expect(codeEl).toBeTruthy();
    expect(codeEl.innerHTML).toContain('token');
  });

  it('renders inline code with custom class', () => {
    const md = 'Use `digitalRead(2)` to check button state.';
    render(<Markdown>{md}</Markdown>);
    const inline = screen.getByText('digitalRead(2)');
    expect(inline.className).toContain('md-inline-code');
  });

  it('renders blockquote callout', () => {
    const md = '> Note: Ensure the pull-down resistor is connected.';
    render(<Markdown>{md}</Markdown>);
    const bq = document.querySelector('.md-blockquote');
    expect(bq).toBeTruthy();
    expect(bq.textContent).toContain('Ensure the pull-down resistor');
  });

  it('renders task lists and checkboxes', () => {
    const md = '- [x] Assemble circuit\n- [ ] Upload Arduino sketch';
    render(<Markdown>{md}</Markdown>);
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBe(2);
    expect(checkboxes[0].checked).toBe(true);
    expect(checkboxes[1].checked).toBe(false);
  });

  it('renders callout alert boxes for [!NOTE] and [!TIP]', () => {
    const md = '> [!NOTE]\n> Keep this in mind when wiring.';
    render(<Markdown>{md}</Markdown>);
    expect(screen.getByRole('note')).toBeTruthy();
    expect(screen.getByText('Note')).toBeTruthy();
    expect(screen.getByText('Keep this in mind when wiring.')).toBeTruthy();
  });

  it('renders thinking disclosure blocks for <think> tags', () => {
    const md = '<think>\nChecking pin 13 configuration...\n</think>\nThe circuit is complete.';
    render(<Markdown>{md}</Markdown>);
    expect(screen.getByText(/Thought process/i)).toBeTruthy();
    expect(screen.getByText('The circuit is complete.')).toBeTruthy();
  });

  it('auto-closes dangling unclosed code blocks from streaming', () => {
    const streamingMd = 'Here is the code:\n```python\nprint("Hello")';
    render(<Markdown>{streamingMd}</Markdown>);
    expect(screen.getByText('Python')).toBeTruthy();
    expect(screen.getByText('print')).toBeTruthy();
    expect(screen.getByText('"Hello"')).toBeTruthy();
  });

  it('renders inline math formulas like $d_{model}$ with subscript', () => {
    const md = 'The hidden dimension is $d_{model}$ in transformers.';
    render(<Markdown>{md}</Markdown>);
    const inlineMath = document.querySelector('.md-inline-math');
    expect(inlineMath).toBeTruthy();
    const sub = inlineMath.querySelector('.math-sub');
    expect(sub).toBeTruthy();
    expect(sub.textContent).toContain('model');
  });

  it('renders block math formulas with Sine/Cosine and fractions', () => {
    const md = 'Positional encoding formula:\n\n$$PE_{(pos, 2i)} = \\sin(pos / 10000^{2i/d_{model}})$$';
    render(<Markdown>{md}</Markdown>);
    const blockMath = document.querySelector('.md-block-math');
    expect(blockMath).toBeTruthy();
    expect(blockMath.textContent).toContain('sin');
    expect(blockMath.textContent).toContain('10000');
    expect(screen.getByRole('button', { name: 'Copy formula' })).toBeTruthy();
  });

  it('preserves currency dollar signs like $50 without turning into math', () => {
    const md = 'The price of the sensor is $50 each, or $100 for two.';
    render(<Markdown>{md}</Markdown>);
    expect(screen.getByText(/The price of the sensor is \$50 each, or \$100 for two/)).toBeTruthy();
  });
});
