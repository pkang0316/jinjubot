import { HomeClient } from "./home-client";
import { getPublishedFeedUrl } from "@/lib/digest";

export default async function HomePage() {
  const publishedFeedUrl = await getPublishedFeedUrl();

  return <HomeClient publishedFeedUrl={publishedFeedUrl} />;
}
