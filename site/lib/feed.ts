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
  start_at?: string | null;
  end_at?: string | null;
  time_summary?: string | null;
  times?: Array<{
    label?: string | null;
    start_at?: string | null;
    end_at?: string | null;
  }>;
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
