import { render, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach, vi } from 'vitest';

// Mock next/navigation before importing the component
vi.mock('next/navigation', () => ({
  usePathname: () => '/',
}));

import { Sidebar } from '@/components/layout/Sidebar';

afterEach(() => {
  cleanup();
});

describe('Sidebar', () => {
  it('renders brand name', () => {
    render(<Sidebar />);
    expect(screen.getByText('CropIntel')).toBeInTheDocument();
  });

  it('renders version footer', () => {
    render(<Sidebar />);
    expect(screen.getByText('Crop Intelligence v0.1.0')).toBeInTheDocument();
  });

  it('renders all navigation items', () => {
    render(<Sidebar />);
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Fields')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
    expect(screen.getByText('Irrigation')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('highlights active nav item', () => {
    render(<Sidebar />);
    // pathname is '/' so Overview should be active
    const overviewLink = screen.getByText('Overview').closest('a');
    expect(overviewLink).toHaveClass('bg-emerald-500/20');
    expect(overviewLink).toHaveClass('text-emerald-400');
  });

  it('renders non-active items with slate styling', () => {
    render(<Sidebar />);
    const fieldsLink = screen.getByText('Fields').closest('a');
    expect(fieldsLink).toHaveClass('text-slate-400');
  });

  it('renders navigation links with correct hrefs', () => {
    render(<Sidebar />);
    const overviewLink = screen.getByText('Overview').closest('a');
    expect(overviewLink).toHaveAttribute('href', '/');

    const fieldsLink = screen.getByText('Fields').closest('a');
    expect(fieldsLink).toHaveAttribute('href', '/fields');
  });
});
