import { render, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach } from 'vitest';
import ChartContainer from '@/components/charts/ChartContainer';

afterEach(() => {
  cleanup();
});

describe('ChartContainer', () => {
  it('renders children', () => {
    const { getByText } = render(
      <ChartContainer>
        <span>Chart Here</span>
      </ChartContainer>,
    );
    expect(getByText('Chart Here')).toBeInTheDocument();
  });

  it('applies default styling classes', () => {
    const { container } = render(
      <ChartContainer>
        <div>Content</div>
      </ChartContainer>,
    );
    const wrapper = container.firstElementChild;
    expect(wrapper).toHaveClass('bg-white/5');
    expect(wrapper).toHaveClass('rounded-2xl');
    expect(wrapper).toHaveClass('p-6');
    expect(wrapper).toHaveClass('h-[350px]');
  });

  it('merges custom className', () => {
    const { container } = render(
      <ChartContainer className="extra-chart">
        <div>Content</div>
      </ChartContainer>,
    );
    const wrapper = container.firstElementChild;
    expect(wrapper).toHaveClass('extra-chart');
    expect(wrapper).toHaveClass('bg-white/5');
  });
});
