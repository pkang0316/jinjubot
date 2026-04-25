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
    <div className="topic-pulse">
      {topics.map((topic) => (
        <article className="topic-card" key={topic.name}>
          <div className="topic-card__header">
            <h3>{topic.name}</h3>
            <span>{topic.change}</span>
          </div>
          <div aria-label={`${topic.signal} signal score`} className="topic-card__bar">
            <div style={{ width: `${topic.signal}%` }} />
          </div>
          <p>{topic.note}</p>
        </article>
      ))}
    </div>
  );
}
