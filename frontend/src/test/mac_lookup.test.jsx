import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LookupPopover from '../components/LookupPopover';
import ConversationHeader from '../components/ConversationHeader';
import Composer from '../components/Composer';
import { AuthProvider } from '../context/AuthContext';
import { SettingsProvider } from '../context/SettingsContext';
import { ChatProvider } from '../context/ChatContext';

const sampleMedia = [
  {
    id: 'att_1',
    name: 'Report_Template.pdf',
    kind: 'document',
    pages: 18,
    chars: 14200,
    extracted_text: 'Department of Mechanical Engineering Presentation covering hydropower, CNC machinery, and robotics.',
  },
  {
    id: 'att_2',
    name: 'avatar.jpeg',
    kind: 'image',
    ocr_used: 1,
    image_description: 'Industrial robotic arm welding a metal workpiece with sparks flying.',
  },
];

const sampleArtifacts = [
  {
    id: 'art_1',
    title: 'Report_Template_Summary.pdf',
    kind: 'pdf',
    file_size: 43520,
    pages: 1,
    summary_text: 'Summary report of the mechanical engineering presentation.',
    download_url: '/api/artifacts/art_1/download',
    view_url: '/api/artifacts/art_1/file',
  },
];

describe('LookupPopover (Reusable Dictionary Content Modal)', () => {
  it('renders media contents cleanly in dictionary layout', () => {
    const items = [
      {
        id: '1',
        name: 'Report_Template.pdf',
        meta: '| document · 18p · 14,200 chars |',
        content: 'Department of Mechanical Engineering Presentation covering hydropower, CNC machinery, and robotics.',
      },
    ];

    render(
      <LookupPopover
        title="Media"
        items={items}
        onClose={() => {}}
      />,
    );

    expect(screen.getByText('Media')).toBeTruthy();
    expect(screen.getAllByText('1').length).toBe(2);
    expect(screen.getByText('Report_Template.pdf')).toBeTruthy();
    expect(screen.getByText('| document · 18p · 14,200 chars |')).toBeTruthy();
    expect(screen.getByText(/Department of Mechanical Engineering Presentation/)).toBeTruthy();
  });

  it('renders artifacts contents cleanly with the same reusable component', () => {
    const items = [
      {
        id: 'art_1',
        name: 'Report_Template_Summary.pdf',
        meta: '| pdf · 42.5 KB · 1p |',
        content: 'Summary report of the mechanical engineering presentation.',
        url: '/api/artifacts/art_1/file',
      },
    ];

    render(
      <LookupPopover
        title="Artifacts"
        items={items}
        onClose={() => {}}
      />,
    );

    expect(screen.getByText('Artifacts')).toBeTruthy();
    expect(screen.getByText('Report_Template_Summary.pdf')).toBeTruthy();
    expect(screen.getByText('| pdf · 42.5 KB · 1p |')).toBeTruthy();
    expect(screen.getByText(/Summary report of the mechanical engineering presentation/)).toBeTruthy();
  });

  it('renders empty states gracefully', () => {
    render(
      <LookupPopover
        title="Media"
        items={[]}
        emptyMessage="No files attached to this chat yet."
      />,
    );

    expect(screen.getByText('No files attached to this chat yet.')).toBeTruthy();
  });
});

describe('ConversationHeader with separate Media and Artifacts in Top Right Corner', () => {
  it('opens separate popovers when clicking Media and Artifacts buttons in top right corner', async () => {
    render(
      <ConversationHeader
        title="Test Chat"
        media={sampleMedia}
        artifacts={sampleArtifacts}
      />,
    );

    const mediaBtn = screen.getByRole('button', { name: /media attached, 2 files/i });
    const artifactsBtn = screen.getByRole('button', { name: /generated artifacts, 1 items/i });

    // Click Media: opens Media popover
    await userEvent.click(mediaBtn);
    expect(screen.getByRole('dialog', { name: /media contents/i })).toBeTruthy();
    expect(screen.getByText('Report_Template.pdf')).toBeTruthy();
    expect(screen.queryByText('Report_Template_Summary.pdf')).toBeNull(); // artifacts not mixed in!

    // Click Artifacts: opens separate Artifacts popover
    await userEvent.click(artifactsBtn);
    expect(screen.getByRole('dialog', { name: /artifacts contents/i })).toBeTruthy();
    expect(screen.getByText('Report_Template_Summary.pdf')).toBeTruthy();
    expect(screen.queryByText('Report_Template.pdf')).toBeNull(); // media not mixed in!
  });
});

describe('Composer with model selection inside input box', () => {
  it('renders the model selector inside the composer toolbar', () => {
    render(
      <AuthProvider>
        <SettingsProvider>
          <ChatProvider>
            <Composer />
          </ChatProvider>
        </SettingsProvider>
      </AuthProvider>,
    );

    const select = screen.getByRole('combobox', { name: /model/i });
    expect(select).toBeTruthy();
    expect(select.classList.contains('composer-model-select')).toBe(true);
  });
});
