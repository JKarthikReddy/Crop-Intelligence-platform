import { render, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach } from 'vitest';
import { Navbar } from '@/components/layout/Navbar';

afterEach(() => {
  cleanup();
});

describe('Navbar', () => {
  it('renders farm selector with default farm name', () => {
    render(<Navbar />);
    expect(screen.getByText('Green Valley Farm')).toBeInTheDocument();
  });

  it('renders admin label', () => {
    render(<Navbar />);
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  it('renders as a header element', () => {
    render(<Navbar />);
    const header = document.querySelector('header');
    expect(header).toBeInTheDocument();
  });

  it('uses sticky positioning', () => {
    render(<Navbar />);
    const header = document.querySelector('header');
    expect(header).toHaveClass('sticky');
    expect(header).toHaveClass('top-0');
  });
});
