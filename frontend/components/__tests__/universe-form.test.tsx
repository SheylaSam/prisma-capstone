import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { UniverseForm } from '../universe-form';

describe('UniverseForm', () => {
  it('renders all form fields', () => {
    render(<UniverseForm onSubmit={vi.fn()} />);
    expect(screen.getByLabelText('Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Region')).toBeInTheDocument();
    expect(screen.getByLabelText('Ticker (kommagetrennt)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Universum erstellen/i })).toBeInTheDocument();
  });

  it('calls onSubmit with parsed ticker array', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<UniverseForm onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'My Universe' } });
    fireEvent.change(screen.getByLabelText('Region'), { target: { value: 'US' } });
    fireEvent.change(screen.getByLabelText('Ticker (kommagetrennt)'), {
      target: { value: 'aapl, msft, googl' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Universum erstellen/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        name: 'My Universe',
        region: 'US',
        tickers: ['AAPL', 'MSFT', 'GOOGL'],
      });
    });
  });

  it('shows error message when error prop is set', () => {
    render(<UniverseForm onSubmit={vi.fn()} error="Name bereits vergeben" />);
    expect(screen.getByText('Name bereits vergeben')).toBeInTheDocument();
  });

  it('disables button and inputs while submitting', () => {
    render(<UniverseForm onSubmit={vi.fn()} isSubmitting />);
    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByLabelText('Name')).toBeDisabled();
  });
});
