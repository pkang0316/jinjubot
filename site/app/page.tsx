import { FeedTabs } from "./feed-tabs";
import { getDigest } from "@/lib/digest";
import styles from "./page.module.css";

export default async function HomePage() {
  const digest = await getDigest();
  const rankedItems = [...digest.items].sort((left, right) => right.interest_rating - left.interest_rating);
  const hotPicks = rankedItems.slice(0, 3);

  return (
    <main className={styles.shell}>
      <section className={styles.heroBackdrop} aria-hidden="true">
        <div className={styles.heroWash} />
        <div className={styles.heroLines} />
      </section>

      <section className={styles.hotPicksSection}>
        <div className={styles.hotPicksHeader}>
          <p className={styles.eyebrow}>Hot picks</p>
        </div>

        <div className={styles.hotPicksGrid}>
          {hotPicks.map((item) => (
            <article className={styles.hotPickCard} key={item.id}>
              <a className={styles.hotPickImageLink} href={item.url} aria-label={item.title}>
                {item.image_url ? (
                  <img className={styles.hotPickImage} src={item.image_url} alt={item.title} />
                ) : (
                  <div className={styles.hotPickPlaceholder} aria-hidden="true" />
                )}
              </a>

              <div className={styles.hotPickBody}>
                <span className={styles.categoryPill}>{item.category}</span>
                <h2>
                  <a href={item.url}>{item.title}</a>
                </h2>
                <p>{item.description}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.feedSection}>
        <FeedTabs items={rankedItems} />
      </section>
    </main>
  );
}
