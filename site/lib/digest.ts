import fs from "node:fs/promises";
import path from "node:path";

export type Category = "events" | "food" | "deals";

export type ItemStatus = "active" | "expired" | "removed";

export type Source = {
  name: string;
  url: string;
  type: string;
};

export type FeedItem = {
  id: string;
  version: number;
  category: Category;
  title: string;
  description: string;
  url: string;
  image_url?: string;
  source: Source;
  discovered_at: string;
  updated_at: string;
  last_seen_at: string;
  tags: string[];
  interest_rating: number;
  confidence: number;
  status: ItemStatus;
  reason: string;
};

export type FeedData = {
  siteTitle: string;
  tagline: string;
  updatedAt: string;
  summary: string;
  items: FeedItem[];
};

export async function getDigest(): Promise<FeedData> {
  const contentPath = path.join(process.cwd(), "..", "content", "research-digest.json");
  const file = await fs.readFile(contentPath, "utf8");
  return JSON.parse(file) as FeedData;
}
