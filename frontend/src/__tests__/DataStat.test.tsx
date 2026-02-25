import { render, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach } from 'vitest';
import DataStat from '@/components/ui/DataStat';
import { TrendingUp } from 'lucide-react';

afterEach(() => {
  cleanup();
});

describe('DataStat', () => {
  it('renders label and value', () => {
    render(<DataStat label="Yield" value="4.5 t/ha" />);
    expect(screen.getByText('Yield')).toBeInTheDocument();
    expect(screen.getByText('4.5 t/ha')).toBeInTheDocument();
  });

  it('renders trend when provided', () => {
    render(<DataStat label="Yield" value="4.5" trend="+12% vs last season" />);
    expect(screen.getByText('+12% vs last season')).toBeInTheDocument();
  });

  it('does not render trend when omitted', () => {
    const { container } = render(<DataStat label="pH" value="6.5" />);
    // No trend paragraph rendered
    const paragraphs = container.querySelectorAll('p');
    // label + value = 2 paragraphs, no trend
    expect(paragraphs.length).toBe(2);
  });

  it('applies positive trend styling', () => {
    render(<DataStat label="Yield" value="4.5" trend="+10%" trendType="positive" />);
    const trend = screen.getByText('+10%');
    expect(trend).toHaveClass('text-emerald-400');
  });

  it('applies negative trend styling', () => {
    render(<DataStat label="Yield" value="4.5" trend="-5%" trendType="negative" />);
    const trend = screen.getByText('-5%');
    expect(trend).toHaveClass('text-red-400');
  });

  it('renders icon when provided', () => {
    const { container } = render(<DataStat label="Growth" value="OK" icon={TrendingUp} />);
    // Icon is wrapped in a div with emerald classes
    const iconWrapper = container.querySelector('.text-emerald-400');
    expect(iconWrapper).toBeInTheDocument();
  });

  it('merges custom className', () => {
    const { container } = render(<DataStat label="X" value="Y" className="extra-class" />);
    // The outer Card div should have the extra class
    const card = container.firstElementChild;
    expect(card).toHaveClass('extra-class');
  });
});
