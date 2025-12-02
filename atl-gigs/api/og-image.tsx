export const config = {
  runtime: "edge",
};

export default async function handler(request: Request) {
  const { searchParams } = new URL(request.url);
  const imageUrl = searchParams.get("image");

  const fallbackUrl = "https://atl-gigs.info/atlgigs.png";
  const target = imageUrl || fallbackUrl;

  try {
    const MAX_IMAGE_BYTES = 5 * 1024 * 1024; // 5MB guardrail
    const res = await fetch(target);

    if (!res.ok) {
      throw new Error(`fetch failed with status ${res.status}`);
    }

    const buffer = await res.arrayBuffer();
    if (buffer.byteLength === 0) {
      throw new Error("empty image response");
    }
    if (buffer.byteLength > MAX_IMAGE_BYTES) {
      throw new Error(`image too large (${buffer.byteLength} bytes)`);
    }

    const contentType = res.headers.get("content-type") || "image/jpeg";

    return new Response(buffer, {
      status: 200,
      headers: {
        "content-type": contentType,
        "cache-control": "public, max-age=3600",
        "content-length": buffer.byteLength.toString(),
      },
    });
  } catch (error) {
    const message = (error as Error).message;
    // Final fallback: return a tiny SVG placeholder to avoid empty body
    const placeholder = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"><rect width="1200" height="630" fill="#0b0c10"/><text x="50%" y="50%" fill="#e5e7eb" font-size="48" font-family="Arial" dominant-baseline="middle" text-anchor="middle">ATL Gigs</text></svg>`;
    return new Response(placeholder, {
      status: 200,
      headers: {
        "content-type": "image/svg+xml",
        "cache-control": "public, max-age=300",
        "x-og-fallback": message,
      },
    });
  }
}
