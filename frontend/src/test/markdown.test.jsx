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
});
