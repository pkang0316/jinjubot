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

export function rankFeedItems(items: FeedItem[]): FeedItem[] {
  return [...items].sort((left, right) => right.interest_rating - left.interest_rating);
}
