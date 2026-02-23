'use client';

import { motion } from 'framer-motion';
import { TrendingUp, Droplets, Thermometer, Sprout, CloudRain, Wind, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Sidebar } from '@/components/layout/Sidebar';
import { Navbar } from '@/components/layout/Navbar';
import { DataStat } from '@/components/ui/DataStat';
import { Card } from '@/components/ui/Card';
import { YieldChart } from '@/components/charts/YieldChart';
import { NDVIChart } from '@/components/charts/NDVIChart';
import { pageFade } from '@/lib/motion';

const yieldData = [
  { month: 'Jan', yield: 2.4 },
  { month: 'Feb', yield: 2.8 },
  { month: 'Mar', yield: 3.1 },
  { month: 'Apr', yield: 3.5 },
  { month: 'May', yield: 4.0 },
  { month: 'Jun', yield: 4.2 },
  { month: 'Jul', yield: 3.9 },
  { month: 'Aug', yield: 4.5 },
  { month: 'Sep', yield: 4.8 },
  { month: 'Oct', yield: 4.3 },
  { month: 'Nov', yield: 3.6 },
  { month: 'Dec', yield: 2.9 },
];

const ndviData = [
  { week: 'W1', ndvi: 0.32 },
  { week: 'W2', ndvi: 0.38 },
  { week: 'W3', ndvi: 0.45 },
  { week: 'W4', ndvi: 0.52 },
  { week: 'W5', ndvi: 0.61 },
  { week: 'W6', ndvi: 0.67 },
  { week: 'W7', ndvi: 0.72 },
  { week: 'W8', ndvi: 0.75 },
  { week: 'W9', ndvi: 0.71 },
  { week: 'W10', ndvi: 0.68 },
];

const weatherSummary = [
  { label: 'Temperature', value: '24°C', icon: Thermometer },
  { label: 'Rainfall', value: '12mm', icon: CloudRain },
  { label: 'Wind Speed', value: '8 km/h', icon: Wind },
  { label: 'UV Index', value: 'Moderate', icon: Sun },
];

export default function Home() {
  const [apiYield, setApiYield] = useState<{ month: string; value: number }[] | null>(null);

  useEffect(() => {
    fetch('/api/yield')
      .then((res) => res.json())
      .then((data: { forecast: { month: string; value: number }[] }) => setApiYield(data.forecast))
      .catch(() => {
        /* use static data as fallback */
      });
  }, []);

  return (
    <div className="flex min-h-screen bg-background text-white">
      <Sidebar />

      {/* Main Content */}
      <div className="flex flex-1 flex-col pl-64">
        <Navbar />

        <motion.main {...pageFade} className="flex-1 space-y-6 p-6">
          {/* Page Header */}
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-sm text-gray-400">Real-time crop intelligence overview</p>
          </div>

          {/* KPI Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <DataStat
              label="Avg Yield"
              value="4.2 t/ha"
              trend="+12% vs last season"
              trendType="positive"
              icon={TrendingUp}
            />
            <DataStat
              label="Soil Moisture"
              value="68%"
              trend="Optimal range"
              trendType="positive"
              icon={Droplets}
            />
            <DataStat
              label="Temperature"
              value="24°C"
              trend="+2°C above avg"
              trendType="negative"
              icon={Thermometer}
            />
            <DataStat
              label="Crop Health"
              value="Good"
              trend="NDVI: 0.72"
              trendType="positive"
              icon={Sprout}
            />
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <YieldChart data={yieldData} />
            <NDVIChart data={ndviData} />
          </div>

          {/* Weather Summary Panel */}
          <Card variant="default" className="space-y-4">
            <h3 className="text-lg font-semibold">Weather Summary</h3>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {weatherSummary.map((item) => (
                <div key={item.label} className="flex items-center gap-3 rounded-xl bg-white/5 p-4">
                  <item.icon className="h-5 w-5 text-primary" />
                  <div>
                    <p className="text-xs text-gray-400">{item.label}</p>
                    <p className="text-sm font-mono font-semibold">{item.value}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* API Data Preview */}
          {apiYield && (
            <Card variant="default" className="space-y-2">
              <h3 className="text-lg font-semibold">API Yield Data</h3>
              <p className="text-sm text-gray-400">
                Fetched from <code className="text-primary">/api/yield</code>
              </p>
              <div className="flex gap-4">
                {apiYield.map((item) => (
                  <div key={item.month} className="rounded-lg bg-white/5 px-4 py-2 text-center">
                    <p className="text-xs text-gray-400">{item.month}</p>
                    <p className="font-mono text-sm font-bold text-primary">{item.value}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </motion.main>
      </div>
    </div>
  );
}
