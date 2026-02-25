import { render, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach } from 'vitest';
import { Button } from '@/components/ui/Button';

afterEach(() => {
  cleanup();
});

describe('Button', () => {
  it('renders children text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('renders as a button element', () => {
    render(<Button>Submit</Button>);
    expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument();
  });

  it('applies default variant classes', () => {
    render(<Button data-testid="btn">Go</Button>);
    const btn = screen.getByTestId('btn');
    expect(btn).toHaveClass('bg-emerald-600');
  });

  it('applies outline variant classes', () => {
    render(
      <Button variant="outline" data-testid="btn">
        Go
      </Button>,
    );
    const btn = screen.getByTestId('btn');
    expect(btn).toHaveClass('border');
    expect(btn).toHaveClass('bg-transparent');
  });

  it('applies ghost variant classes', () => {
    render(
      <Button variant="ghost" data-testid="btn">
        Go
      </Button>,
    );
    const btn = screen.getByTestId('btn');
    expect(btn).toHaveClass('hover:bg-white/10');
  });

  it('applies size sm', () => {
    render(
      <Button size="sm" data-testid="btn">
        S
      </Button>,
    );
    expect(screen.getByTestId('btn')).toHaveClass('h-8');
  });

  it('applies size lg', () => {
    render(
      <Button size="lg" data-testid="btn">
        L
      </Button>,
    );
    expect(screen.getByTestId('btn')).toHaveClass('h-12');
  });

  it('merges custom className', () => {
    render(
      <Button className="my-custom" data-testid="btn">
        X
      </Button>,
    );
    expect(screen.getByTestId('btn')).toHaveClass('my-custom');
  });

  it('passes through native button props', () => {
    render(
      <Button disabled data-testid="btn">
        Off
      </Button>,
    );
    expect(screen.getByTestId('btn')).toBeDisabled();
  });
});
