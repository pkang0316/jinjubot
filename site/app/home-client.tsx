"use client";

import { useEffect, useMemo, useState } from "react";
import { FeedTabs } from "./feed-tabs";
import type { FeedData } from "@/lib/feed";
import { rankFeedItems } from "@/lib/feed";
import styles from "./page.module.css";

const heroDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric"
});

type HomeClientProps = {
  publishedFeedUrl: string;
};

export function HomeClient({ publishedFeedUrl }: HomeClientProps) {
  const [digest, setDigest] = useState<FeedData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [remoteFetchFailed, setRemoteFetchFailed] = useState(false);

  useEffect(() => {
    if (!publishedFeedUrl) {
      setIsLoading(false);
      setRemoteFetchFailed(true);
      return;
    }

    const controller = new AbortController();

    async function refreshDigest() {
      try {
        const response = await fetch(publishedFeedUrl, {
          signal: controller.signal,
          headers: {
            Accept: "application/json"
          }
        });

        if (!response.ok) {
          throw new Error(`Published feed request failed with ${response.status}`);
        }

        const nextDigest = (await response.json()) as FeedData;
        setDigest(nextDigest);
        setRemoteFetchFailed(false);
      } catch {
        if (controller.signal.aborted) {
          return;
        }

        setRemoteFetchFailed(true);
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void refreshDigest();

    return () => controller.abort();
  }, [publishedFeedUrl]);

  const rankedItems = useMemo(() => rankFeedItems(digest?.items ?? []), [digest?.items]);
  const updatedLabel = digest ? heroDateFormatter.format(new Date(digest.updatedAt)) : "";

  if (isLoading) {
    return (
      <main className={styles.shell}>
        <section className={styles.heroBackdrop} aria-hidden="true">
          <div className={styles.heroWash} />
          <div className={styles.heroLines} />
        </section>
        <section className={styles.stateSection}>
          <img className={styles.heroMascotInline} src="/images/jinju1.png" alt="" aria-hidden="true" />
          <div className={styles.stateCopy}>
            <h1>Loading picks...</h1>
            <p>Fetching the latest feed.</p>
          </div>
        </section>
      </main>
    );
  }

  if (!digest || remoteFetchFailed) {
    return (
      <main className={styles.shell}>
        <section className={styles.heroBackdrop} aria-hidden="true">
          <div className={styles.heroWash} />
          <div className={styles.heroLines} />
        </section>
        <section className={styles.stateSection}>
          <img className={styles.heroMascotInline} src="/images/jinju1.png" alt="" aria-hidden="true" />
          <div className={styles.stateCopy}>
            <h1>Feed unavailable</h1>
            <p>We couldn't load the latest picks right now. Try refreshing in a moment.</p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className={styles.shell}>
      <section className={styles.heroBackdrop} aria-hidden="true">
        <div className={styles.heroWash} />
        <div className={styles.heroLines} />
      </section>

      <section className={styles.heroSimple}>
        <div className={styles.heroCopy}>
          <img
            className={styles.heroMascotInline}
            src="/images/jinju1.png"
            alt="Illustrated black-and-white dog mascot peeking into the local picks board"
          />
          <div className={styles.heroContent}>
            <h1>Jinju picks</h1>
            <p className={styles.heroMeta}>
              Fresh on {updatedLabel} <span aria-hidden="true">&middot;</span> {digest.items.length} local finds
            </p>
          </div>
        </div>
      </section>

      <section className={styles.feedSection}>
        <FeedTabs items={rankedItems} />
      </section>
    </main>
  );
}
