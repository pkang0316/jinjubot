"use client";

import { useMemo, useState } from "react";
import type { Category, FeedItem } from "@/lib/feed";
import styles from "./page.module.css";

const sourceFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric"
});

const tabs: Array<{ key: Category; label: string }> = [
  { key: "events", label: "Events" },
  { key: "food", label: "Food" },
  { key: "deals", label: "Deals" }
];

type FeedTabsProps = {
  items: FeedItem[];
};

export function FeedTabs({ items }: FeedTabsProps) {
  const [activeTab, setActiveTab] = useState<Category>("events");
  const filteredItems = useMemo(
    () => items.filter((item) => item.category === activeTab),
    [activeTab, items]
  );

  return (
    <>
      <div className={styles.tabRow} role="tablist" aria-label="Content categories">
        {tabs.map((tab) => {
          const count = items.filter((item) => item.category === tab.key).length;
          const isActive = tab.key === activeTab;

          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`${styles.tabButton} ${isActive ? styles.tabButtonActive : ""}`}
              onClick={() => setActiveTab(tab.key)}
            >
              <span>{tab.label}</span>
              <strong>{count}</strong>
            </button>
          );
        })}
      </div>

      <div className={styles.feedList}>
        {filteredItems.map((item) => (
          <article className={`${styles.feedCard} ${item.image_url ? "" : styles.feedCardNoImage}`} key={item.id}>
            {item.image_url ? (
              <a
                className={styles.feedImageLink}
                href={item.url}
                aria-label={item.title}
                target="_blank"
                rel="noopener noreferrer"
              >
                <img className={styles.feedImage} src={item.image_url} alt={item.title} />
              </a>
            ) : null}

            <div className={styles.feedBody}>
              <div className={styles.feedTopline}>
                <span className={styles.categoryPill}>{item.category}</span>
                <a href={item.source.url} target="_blank" rel="noopener noreferrer">
                  {item.source.name}
                </a>
                <span>Seen {sourceFormatter.format(new Date(item.last_seen_at))}</span>
              </div>

              <h3>
                <a href={item.url} target="_blank" rel="noopener noreferrer">
                  {item.title}
                </a>
              </h3>
              {item.time_summary ? <p className={styles.itemTime}>{item.time_summary}</p> : null}
              <p className={styles.description}>{item.description}</p>
              <p className={styles.reason}>{item.reason}</p>

              <div className={styles.tagRow}>
                {item.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
