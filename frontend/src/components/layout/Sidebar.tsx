'use client';

import { cn } from '@/lib/utils';
import { LayoutDashboard, Map, BarChart3, Droplets, Settings, Leaf } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navItems = [
  { label: 'Overview', href: '/', icon: LayoutDashboard },
  { label: 'Fields', href: '/fields', icon: Map },
  { label: 'Analytics', href: '/analytics', icon: BarChart3 },
  { label: 'Irrigation', href: '/irrigation', icon: Droplets },
  { label: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r border-white/10 bg-slate-900/80 backdrop-blur-xl">
      {/* Brand */}
      <div className="flex h-16 items-center gap-2 border-b border-white/10 px-6">
        <Leaf className="h-6 w-6 text-emerald-400" />
        <span className="text-lg font-semibold tracking-tight">CropIntel</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white',
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-white/10 px-6 py-4">
        <p className="text-xs text-slate-500">Crop Intelligence v0.1.0</p>
      </div>
    </aside>
  );
}
