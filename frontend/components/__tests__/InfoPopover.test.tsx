import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import { InfoPopover } from '../InfoPopover';

describe('InfoPopover', () => {
  it('rendert Icon-Trigger mit korrektem aria-label', () => {
    render(
      <InfoPopover ariaLabel="Info zu Quality">
        <p>Quality-Beschreibung</p>
      </InfoPopover>,
    );
    expect(screen.getByRole('button', { name: 'Info zu Quality' })).toBeInTheDocument();
  });

  it('Popover-Content initial nicht sichtbar', () => {
    render(
      <InfoPopover ariaLabel="Info zu Quality">
        <p>Quality-Beschreibung</p>
      </InfoPopover>,
    );
    expect(screen.queryByText('Quality-Beschreibung')).not.toBeInTheDocument();
  });

  it('Klick auf Trigger öffnet Popover', () => {
    render(
      <InfoPopover ariaLabel="Info zu Quality">
        <p>Quality-Beschreibung</p>
      </InfoPopover>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Info zu Quality' }));
    expect(screen.getByText('Quality-Beschreibung')).toBeInTheDocument();
  });

  it('Klick auf Trigger ruft stopPropagation auf (kein Parent-onClick)', () => {
    const parentClick = vi.fn();
    render(
      <div onClick={parentClick}>
        <InfoPopover ariaLabel="Info zu Quality">
          <p>Quality-Beschreibung</p>
        </InfoPopover>
      </div>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Info zu Quality' }));
    expect(parentClick).not.toHaveBeenCalled();
  });

  it('Escape-Taste schließt geöffnetes Popover', () => {
    render(
      <InfoPopover ariaLabel="Info zu Quality">
        <p>Quality-Beschreibung</p>
      </InfoPopover>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Info zu Quality' }));
    expect(screen.getByText('Quality-Beschreibung')).toBeInTheDocument();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByText('Quality-Beschreibung')).not.toBeInTheDocument();
  });

  it('rendert Top-Border bei topBorderColor-Prop', () => {
    render(
      <InfoPopover ariaLabel="Info" topBorderColor="hsl(var(--model-quality))">
        <p>Content</p>
      </InfoPopover>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Info' }));
    const content = screen.getByText('Content').parentElement;
    expect(content?.style.borderTopWidth).toBe('4px');
    expect(content?.style.borderTopColor).toBe('hsl(var(--model-quality))');
  });

  it('kein Top-Border ohne topBorderColor', () => {
    render(
      <InfoPopover ariaLabel="Info">
        <p>Content</p>
      </InfoPopover>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Info' }));
    const content = screen.getByText('Content').parentElement;
    expect(content?.style.borderTopWidth).toBeFalsy();
  });
});
