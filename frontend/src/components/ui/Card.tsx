import { cva } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const cardVariants = cva('rounded-2xl backdrop-blur-md border shadow-lg p-6 transition-all', {
  variants: {
    variant: {
      default: 'bg-white/5 border-white/10',
      elevated: 'bg-white/10 border-white/20',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
});

export function Card({
  className,
  variant,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  variant?: 'default' | 'elevated';
}) {
  return <div className={cn(cardVariants({ variant }), className)} {...props} />;
}
