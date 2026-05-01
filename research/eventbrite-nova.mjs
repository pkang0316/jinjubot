import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "..");
const infraEnvPath = path.join(rootDir, "infra", ".env.local");
const contentDir = path.join(rootDir, "content");
const digestPath = path.join(contentDir, "research-digest.json");

const LISTING_URL =
  process.env.EVENTBRITE_NOVA_URL ??
  "https://www.eventbrite.com/d/va--northern-virginia/events/";
const MAX_CANDIDATE_URLS = Number.parseInt(process.env.EVENTBRITE_MAX_CANDIDATES ?? "10", 10);
const MAX_DEEP_FETCHES = Number.parseInt(process.env.EVENTBRITE_MAX_EVENTS ?? "4", 10);

function parseEnvLine(line) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) {
    return null;
  }

  const parts = trimmed.split("=", 2);
  if (parts.length !== 2) {
    return null;
  }

  return {
    key: parts[0].trim(),
    value: parts[1].trim(),
  };
}

async function loadInfraEnv() {
  try {
    const raw = await readFile(infraEnvPath, "utf8");
    for (const line of raw.split(/\r?\n/)) {
      const parsed = parseEnvLine(line);
      if (!parsed) {
        continue;
      }

      if (!(parsed.key in process.env)) {
        process.env[parsed.key] = parsed.value;
      }
    }
  } catch {
    // Optional local env file.
  }
}

function getGatewayBaseUrl() {
  return (
    process.env.JINJUBOT_GATEWAY_URL ??
    process.env.LOCAL_LLM_GATEWAY_URL ??
    process.env.CF_LLM_GATEWAY_URL ??
    "http://localhost:8080"
  ).replace(/\/+$/, "");
}

function getGatewayHeaders() {
  const headers = {
    "Content-Type": "application/json",
  };

  const baseUrl = getGatewayBaseUrl();
  const isPublicAccessUrl = /^https:\/\/llm\./i.test(baseUrl);

  if (isPublicAccessUrl) {
    if (!process.env.CF_ACCESS_CLIENT_ID || !process.env.CF_ACCESS_CLIENT_SECRET) {
      throw new Error(
        "CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET are required when using the public Cloudflare gateway."
      );
    }

    headers["CF-Access-Client-ID"] = process.env.CF_ACCESS_CLIENT_ID;
    headers["CF-Access-Client-Secret"] = process.env.CF_ACCESS_CLIENT_SECRET;
  }

  return headers;
}

async function fetchHtml(url) {
  const response = await fetch(url, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`);
  }

  return response.text();
}

function stripTags(html) {
  return html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, " ")
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, " ")
    .replace(/<noscript\b[^<]*(?:(?!<\/noscript>)<[^<]*)*<\/noscript>/gi, " ")
    .replace(/<[^>]+>/g, " ");
}

function decodeHtml(text) {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">");
}

function htmlToCondensedText(html) {
  return decodeHtml(stripTags(html))
    .replace(/\s+/g, " ")
    .replace(/ ?([,.;:!?])/g, "$1")
    .trim();
}

function normalizeEventbriteUrl(rawUrl) {
  try {
    const url = new URL(rawUrl, LISTING_URL);
    url.search = "";
    url.hash = "";
    return url.toString();
  } catch {
    return null;
  }
}

function normalizeOptionalUrl(rawUrl, baseUrl) {
  if (typeof rawUrl !== "string" || !rawUrl.trim()) {
    return undefined;
  }

  try {
    return new URL(rawUrl.trim(), baseUrl).toString();
  } catch {
    return rawUrl.trim();
  }
}

function extractCandidateEventUrls(html) {
  const matches = new Set();
  const patterns = [
    /https:\/\/www\.eventbrite\.com\/e\/[^"'`\s<>]+/gi,
    /href="(\/e\/[^"]+)"/gi,
  ];

  for (const pattern of patterns) {
    for (const match of html.matchAll(pattern)) {
      const candidate = match[1] ?? match[0];
      const normalized = normalizeEventbriteUrl(candidate);
      if (!normalized) {
        continue;
      }
      if (!normalized.includes("/e/")) {
        continue;
      }
      matches.add(normalized);
    }
  }

  return Array.from(matches).slice(0, MAX_CANDIDATE_URLS);
}

async function callGateway(endpoint, body) {
  const response = await fetch(`${getGatewayBaseUrl()}${endpoint}`, {
    method: "POST",
    headers: getGatewayHeaders(),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Gateway ${endpoint} failed: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

async function chooseEventUrlsForDeepFetch(listingText, candidateUrls) {
  const response = await callGateway("/plan", {
    context: [
      `Source page: ${LISTING_URL}`,
      "Candidate event detail URLs:",
      ...candidateUrls.map((url) => `- ${url}`),
      "",
      "Listing page text excerpt:",
      listingText.slice(0, 12000),
    ].join("\n"),
    budget: MAX_DEEP_FETCHES,
    additional_instructions: [
      "Choose the most promising event detail pages to inspect more deeply.",
      "Prefer real in-person events relevant to Northern Virginia.",
      "Return tasks with action='deep_fetch_event' and target set to one of the candidate URLs exactly.",
      `Choose at most ${MAX_DEEP_FETCHES} URLs.`,
    ].join(" "),
  });

  const tasks = response?.parsed?.tasks;
  if (!Array.isArray(tasks)) {
    return candidateUrls.slice(0, MAX_DEEP_FETCHES);
  }

  const selected = [];
  for (const task of tasks) {
    const target = typeof task?.target === "string" ? task.target.trim() : "";
    if (!candidateUrls.includes(target)) {
      continue;
    }
    if (!selected.includes(target)) {
      selected.push(target);
    }
  }

  return selected.length > 0 ? selected.slice(0, MAX_DEEP_FETCHES) : candidateUrls.slice(0, MAX_DEEP_FETCHES);
}

function parseTitleFromHtml(html) {
  const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
  return titleMatch ? decodeHtml(titleMatch[1]).replace(/\s+/g, " ").trim() : null;
}

function parseOgImage(html) {
  const match = html.match(/<meta[^>]+property="og:image"[^>]+content="([^"]+)"/i);
  return match ? match[1].trim() : null;
}

function clampNumber(value, min, max, fallback) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return fallback;
  }
  return Math.max(min, Math.min(max, numeric));
}

function makeItemId(url) {
  const slug = url
    .replace(/^https?:\/\//, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();
  const digest = createHash("sha1").update(url).digest("hex").slice(0, 8);
  return `event-${slug}-${digest}`;
}

function normalizeExtractedRecord(record, eventUrl, now, htmlFallbacks) {
  const title = typeof record?.title === "string" && record.title.trim() ? record.title.trim() : htmlFallbacks.title;
  const description =
    typeof record?.description === "string" && record.description.trim()
      ? record.description.trim()
      : "Eventbrite event discovered from the Northern Virginia events listing.";

  if (!title) {
    return null;
  }

  const tags = Array.isArray(record?.tags)
    ? record.tags.map((tag) => String(tag).trim().toLowerCase()).filter(Boolean)
    : [];

  return {
    id: makeItemId(eventUrl),
    version: 1,
    category: "events",
    title,
    description,
    url: eventUrl,
    image_url: normalizeOptionalUrl(record?.image_url, eventUrl) ?? normalizeOptionalUrl(htmlFallbacks.image_url, eventUrl),
    source: {
      name: "Eventbrite",
      url: eventUrl,
      type: "event_marketplace",
    },
    discovered_at: now,
    updated_at: now,
    last_seen_at: now,
    tags,
    interest_rating:
      Number.isFinite(Number(record?.interest_rating)) && Number(record.interest_rating) > 0
        ? Math.round(clampNumber(record.interest_rating, 0, 100, 72))
        : 72,
    confidence: clampNumber(record?.confidence, 0, 1, 0.75),
    status:
      record?.status === "expired" || record?.status === "removed" || record?.status === "active"
        ? record.status
        : "active",
    reason:
      typeof record?.reason === "string" && record.reason.trim()
        ? record.reason.trim()
        : "Selected from the Northern Virginia Eventbrite listing for deeper review.",
  };
}

async function extractEventRecord(eventUrl) {
  const html = await fetchHtml(eventUrl);
  const title = parseTitleFromHtml(html);
  const imageUrl = parseOgImage(html);
  const content = htmlToCondensedText(html).slice(0, 18000);

  const response = await callGateway("/extract", {
    source_url: eventUrl,
    schema_hint: JSON.stringify({
      records: [
        {
          title: "",
          description: "",
          image_url: "",
          tags: [],
          reason: "",
          interest_rating: 0,
          confidence: 0,
          status: "active",
        },
      ],
    }),
    additional_instructions: [
      "Extract at most one event record from this Eventbrite event detail page.",
      "Prefer concise, factual descriptions.",
      "Keep tags short and lowercase.",
      "Use status=active unless the page clearly indicates the event is no longer available.",
      "Return {\"records\": []} if the page does not describe a real event.",
    ].join(" "),
    content,
  });

  const record = Array.isArray(response?.parsed?.records) ? response.parsed.records[0] : null;
  return { record, htmlFallbacks: { title, image_url: imageUrl } };
}

async function readExistingDigest(now) {
  try {
    const raw = await readFile(digestPath, "utf8");
    return JSON.parse(raw);
  } catch {
    return {
      siteTitle: "JinjuBot",
      tagline: "A Washington-area weekend guide that can pivot between events, food, and deals without turning into a cluttered dashboard.",
      updatedAt: now,
      summary: "Generated from live research runs.",
      items: [],
    };
  }
}

async function main() {
  await loadInfraEnv();

  const now = new Date().toISOString();
  const listingHtml = await fetchHtml(LISTING_URL);
  const candidateUrls = extractCandidateEventUrls(listingHtml);

  if (candidateUrls.length === 0) {
    throw new Error("No candidate Eventbrite event URLs were found on the listing page.");
  }

  const listingText = htmlToCondensedText(listingHtml);
  const selectedUrls = await chooseEventUrlsForDeepFetch(listingText, candidateUrls);

  const extractedItems = [];
  for (const eventUrl of selectedUrls) {
    try {
      const { record, htmlFallbacks } = await extractEventRecord(eventUrl);
      const normalized = normalizeExtractedRecord(record, eventUrl, now, htmlFallbacks);
      if (normalized) {
        extractedItems.push(normalized);
      }
    } catch (error) {
      console.warn(`Skipping ${eventUrl}: ${error.message}`);
    }
  }

  if (extractedItems.length === 0) {
    throw new Error("No event records were extracted from the selected Eventbrite detail pages.");
  }

  const existing = await readExistingDigest(now);
  const nonEventItems = Array.isArray(existing.items) ? existing.items.filter((item) => item.category !== "events") : [];

  const payload = {
    siteTitle: existing.siteTitle ?? "JinjuBot",
    tagline:
      existing.tagline ??
      "A Washington-area weekend guide that can pivot between events, food, and deals without turning into a cluttered dashboard.",
    updatedAt: now,
    summary: `Generated from a live Eventbrite Northern Virginia discovery run at ${now}.`,
    items: [...extractedItems, ...nonEventItems],
  };

  await mkdir(contentDir, { recursive: true });
  await writeFile(digestPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");

  console.log(`Wrote ${extractedItems.length} Eventbrite event record(s) to ${digestPath}`);
  console.log(`Deep-fetched URLs:\n- ${selectedUrls.join("\n- ")}`);
}

await main();
