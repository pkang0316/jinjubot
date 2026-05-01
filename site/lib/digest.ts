import path from "node:path";
import fs from "node:fs/promises";

async function readEnvFileVar(fileName: string, name: string): Promise<string | null> {
  const envPath = path.join(process.cwd(), "..", "infra", fileName);

  try {
    const contents = await fs.readFile(envPath, "utf8");
    for (const rawLine of contents.split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#") || !line.includes("=")) {
        continue;
      }

      const [key, ...rest] = line.split("=");
      if (key.trim() === name) {
        return rest.join("=").trim() || null;
      }
    }
  } catch {
    return null;
  }

  return null;
}

export async function getPublishedFeedUrl(): Promise<string> {
  return (
    process.env.NEXT_PUBLIC_JINJUBOT_FEED_URL?.trim() ||
    process.env.JINJUBOT_FEED_URL?.trim() ||
    (await readEnvFileVar(".env.local", "JINJUBOT_FEED_URL")) ||
    (await readEnvFileVar(".env.example", "JINJUBOT_FEED_URL")) ||
    ""
  );
}
