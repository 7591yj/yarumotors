import gps from "../utils/gps.json" assert { type: "json" };

export function getGps(year: string | number): string[] {
  const key = String(year).trim();
  const data = gps as Record<string, string[]>;
  console.log(data[key]);
  return data[key] ?? [];
}
