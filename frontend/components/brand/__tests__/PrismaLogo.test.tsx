import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';

import { PrismaLogo } from '../PrismaLogo';

describe('PrismaLogo', () => {
  it('rendert ein SVG-Element mit viewBox', () => {
    const { container } = render(<PrismaLogo />);
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute('viewBox')).toBe('0 0 24 24');
  });

  it('enthält 5 stop-Elemente für die Spektrum-Farben', () => {
    const { container } = render(<PrismaLogo />);
    const stops = container.querySelectorAll('stop');
    expect(stops).toHaveLength(5);
    const colors = Array.from(stops).map((s) => s.getAttribute('stop-color'));
    expect(colors).toEqual(['#16a34a', '#2563eb', '#ea580c', '#7c3aed', '#eab308']);
  });

  it('reicht className-Prop an SVG durch', () => {
    const { container } = render(<PrismaLogo className="h-6 w-6" />);
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('class')).toMatch(/h-6 w-6/);
  });

  it('hat aria-label für Screenreader', () => {
    const { container } = render(<PrismaLogo />);
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('aria-label')).toBe('PRISMA Logo');
  });
});
