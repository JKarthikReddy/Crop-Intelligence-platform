"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card } from "@/components/ui/Card";

interface YieldDataPoint {
  month: string;
  yield: number;
}

interface YieldChartProps {
  data: YieldDataPoint[];
}

export function YieldChart({ data }: YieldChartProps) {
  return (
    <Card variant="elevated" className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Yield Forecast</h3>
        <p className="text-sm text-slate-400">
          Predicted crop yield (tons/hectare)
        </p>
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="month"
              stroke="rgba(255,255,255,0.3)"
              tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 12 }}
            />
            <YAxis
              stroke="rgba(255,255,255,0.3)"
              tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 12 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(15,23,42,0.9)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "12px",
                color: "#fff",
              }}
            />
            <Line
              type="monotone"
              dataKey="yield"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ fill: "#10b981", strokeWidth: 0, r: 4 }}
              activeDot={{ r: 6, fill: "#34d399" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
