import TopicPulse from "@/src/components/TopicPulse";
import { getDigest } from "@/lib/digest";
import styles from "./page.module.css";

export default async function HomePage() {
  const digest = await getDigest();
  const updatedLabel = new Intl.DateTimeFormat("en-US", {
    dateStyle: "long",
    timeStyle: "short"
  }).format(new Date(digest.updatedAt));

  return (
    <main className={styles.shell}>
      <section className={`${styles.panel} ${styles.hero}`}>
        <div>
          <p className={styles.eyebrow}>Agentic research publishing starter</p>
          <h1>{digest.siteTitle}</h1>
          <p className={styles.lede}>{digest.tagline}</p>
          <p className={styles.summary}>{digest.summary}</p>
        </div>
        <dl className={styles.heroMeta}>
          <div>
            <dt>Cadence</dt>
            <dd>{digest.cadence}</dd>
          </div>
          <div>
            <dt>Last update</dt>
            <dd>{updatedLabel}</dd>
          </div>
          <div>
            <dt>Content source</dt>
            <dd>
              <code>content/research-digest.json</code>
            </dd>
          </div>
        </dl>
      </section>

      <section className={styles.contentGrid}>
        <article className={styles.panel}>
          <div className={styles.sectionHeading}>
            <p className={styles.eyebrow}>Signal board</p>
            <h2>Topics worth watching</h2>
          </div>
          <TopicPulse topics={digest.topics} />
        </article>

        <article className={styles.panel}>
          <div className={styles.sectionHeading}>
            <p className={styles.eyebrow}>Publishing loop</p>
            <h2>How this repo is wired</h2>
          </div>
          <ol className={styles.steps}>
            <li>Run a research job on a daily or weekly schedule.</li>
            <li>Write normalized content into the repo.</li>
            <li>Build static HTML with Next.js.</li>
            <li>Deploy via CI while Terraform manages infrastructure.</li>
          </ol>
        </article>
      </section>

      <section className={`${styles.panel} ${styles.highlights}`}>
        <div className={styles.sectionHeading}>
          <p className={styles.eyebrow}>Starter notes</p>
          <h2>Current highlights</h2>
        </div>
        <ul>
          {digest.highlights.map((highlight) => (
            <li key={highlight}>{highlight}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}
