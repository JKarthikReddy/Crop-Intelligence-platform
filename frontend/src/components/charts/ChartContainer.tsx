import { ReactNode } from 'react';

interface ChartContainerProps {
  children: ReactNode;
  className?: string;
}

export default function ChartContainer({ children, className }: ChartContainerProps) {
  return (
    <div
      className={`bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl p-6 h-[350px] ${className ?? ''}`}
    >
      {children}
    </div>
  );
}
