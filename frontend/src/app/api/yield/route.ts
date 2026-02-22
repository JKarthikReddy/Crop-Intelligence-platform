import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    forecast: [
      { month: "Jan", value: 2.4 },
      { month: "Feb", value: 2.8 },
      { month: "Mar", value: 3.1 },
      { month: "Apr", value: 3.5 },
      { month: "May", value: 4.0 },
      { month: "Jun", value: 4.2 },
      { month: "Jul", value: 3.9 },
      { month: "Aug", value: 4.5 },
      { month: "Sep", value: 4.8 },
      { month: "Oct", value: 4.3 },
      { month: "Nov", value: 3.6 },
      { month: "Dec", value: 2.9 },
    ],
  });
}
