const BASE_URL = process.env.BASE_URL || "http://localhost:3000";
const INTERVAL_MS = Number(process.env.INTERVAL_MS) || 500;

let running = true;
let requestCount = 0;
let successCount = 0;
let errorCount = 0;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchJson(path) {
  const url = `${BASE_URL}${path}`;
  const startedAt = Date.now();

  try {
    const response = await fetch(url);
    const body = await response.json().catch(() => null);
    const durationMs = Date.now() - startedAt;

    requestCount += 1;
    if (response.ok) {
      successCount += 1;
    } else {
      errorCount += 1;
    }

    console.log(
      `[${requestCount}] ${response.status} GET ${path} (${durationMs}ms)`
    );

    return { ok: response.ok, body };
  } catch (error) {
    requestCount += 1;
    errorCount += 1;
    console.error(`[${requestCount}] ERROR GET ${path}: ${error.message}`);
    return { ok: false, body: null };
  }
}

async function sendTraffic() {
  console.log(`Sending traffic to ${BASE_URL} every ${INTERVAL_MS}ms`);
  console.log("Press Ctrl+C to stop\n");

  while (running) {
    const listResult = await fetchJson("/users");

    if (running && listResult.ok && Array.isArray(listResult.body) && listResult.body.length > 0) {
      const randomUser =
        listResult.body[Math.floor(Math.random() * listResult.body.length)];
      await fetchJson(`/users/${randomUser.id}`);
    }

    if (running) {
      await sleep(INTERVAL_MS);
    }
  }
}

function stop() {
  if (!running) {
    return;
  }

  running = false;
  console.log("\nStopping traffic script...");
  console.log(
    `Done. requests=${requestCount} success=${successCount} errors=${errorCount}`
  );
}

process.on("SIGINT", () => {
  stop();
  process.exit(0);
});

process.on("SIGTERM", () => {
  stop();
  process.exit(0);
});

sendTraffic().catch((error) => {
  console.error("Traffic script failed:", error);
  process.exit(1);
});
