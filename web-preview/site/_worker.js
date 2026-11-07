const endpoint = "/tools/baregps-route-planner/terrain/v1/mapzen";
const json = (body, status) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/tools/baregps-route-planner/terrain/"))
      return env.ASSETS.fetch(request);
    if (url.pathname !== endpoint)
      return json({ error: "Unknown terrain endpoint" }, 404);
    if (request.method !== "GET")
      return json({ error: "Use GET for terrain heights" }, 405);
    const values = url.searchParams.getAll("locations");
    if (
      values.length !== 1 ||
      [...url.searchParams.keys()].some((key) => key !== "locations")
    )
      return json({ error: "Provide locations only" }, 400);
    const locations = values[0].split("|");
    if (
      !locations.length ||
      locations.length > 100 ||
      values[0].length > 5000 ||
      !locations.every((value) => {
        const parts = value.split(",");
        return (
          parts.length === 2 &&
          parts.every((part) => /^-?\d+(?:\.\d+)?$/.test(part)) &&
          Math.abs(Number(parts[0])) <= 90 &&
          Math.abs(Number(parts[1])) <= 180
        );
      })
    )
      return json(
        { error: "Provide 1–100 valid latitude,longitude pairs" },
        400,
      );
    const controller = new AbortController(),
      timer = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(
        "https://api.opentopodata.org/v1/mapzen?locations=" +
          encodeURIComponent(locations.join("|")),
        {
          signal: controller.signal,
          headers: { Accept: "application/json" },
          redirect: "manual",
        },
      );
      if (!response.ok)
        return json({ error: "Terrain service is unavailable or busy" }, 503);
      const data = await response.json();
      if (
        data.status !== "OK" ||
        !Array.isArray(data.results) ||
        data.results.length !== locations.length
      )
        return json({ error: "Terrain heights unavailable" }, 502);
      return json(data, 200);
    } catch {
      return json(
        { error: "Terrain service unavailable; try again later" },
        503,
      );
    } finally {
      clearTimeout(timer);
    }
  },
};
