import fs from "node:fs/promises";
import path from "node:path";

export type Topic = {
  name: string;
  signal: number;
  change: string;
  note: string;
};

export type Digest = {
  siteTitle: string;
  tagline: string;
  updatedAt: string;
  cadence: string;
  summary: string;
  topics: Topic[];
  highlights: string[];
};

export async function getDigest(): Promise<Digest> {
  const contentPath = path.join(process.cwd(), "..", "content", "research-digest.json");
  const file = await fs.readFile(contentPath, "utf8");
  return JSON.parse(file) as Digest;
}
