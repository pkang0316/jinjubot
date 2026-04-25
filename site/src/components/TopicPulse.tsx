"use client";

import styles from "./TopicPulse.module.css";

type Topic = {
  name: string;
  signal: number;
  change: string;
  note: string;
};

type Props = {
  topics: Topic[];
};

export default function TopicPulse({ topics }: Props) {
  return (
    <div className={styles.topicPulse}>
      {topics.map((topic) => (
        <article className={styles.topicCard} key={topic.name}>
          <div className={styles.topicCardHeader}>
            <h3>{topic.name}</h3>
            <span>{topic.change}</span>
          </div>
          <div aria-label={`${topic.signal} signal score`} className={styles.topicCardBar}>
            <div style={{ width: `${topic.signal}%` }} />
          </div>
          <p>{topic.note}</p>
        </article>
      ))}
    </div>
  );
}
