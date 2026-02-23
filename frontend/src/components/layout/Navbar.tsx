'use client';

import { Bell, ChevronDown, User } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export function Navbar() {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-white/10 bg-slate-950/80 px-6 backdrop-blur-xl">
      {/* Farm Selector */}
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" className="gap-2">
          <span className="text-sm">Green Valley Farm</span>
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" className="relative">
          <Bell className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-emerald-400" />
        </Button>
        <Button variant="ghost" size="sm" className="gap-2">
          <User className="h-4 w-4" />
          <span className="hidden text-sm sm:inline">Admin</span>
        </Button>
      </div>
    </header>
  );
}
