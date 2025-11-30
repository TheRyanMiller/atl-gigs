import { ImageResponse } from "@vercel/og";

export const config = {
  runtime: "edge",
};

export default async function handler() {
  try {
    const img = new ImageResponse(
      (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "100%",
            height: "100%",
            background: "#0b0c10",
            color: "#e5e7eb",
            fontSize: 64,
            fontWeight: 700,
            letterSpacing: "-0.03em",
          }}
        >
          OG baseline
        </div>
      ),
      { width: 1200, height: 630 }
    );

    const buffer = await img.arrayBuffer();
    const size = buffer.byteLength;

    return new Response(buffer, {
      status: size > 0 ? 200 : 500,
      headers: {
        "content-type": "image/png",
        "cache-control": "public, max-age=300",
        "x-image-size": size.toString(),
        "x-og-test": size > 0 ? "ok" : "empty-buffer",
      },
    });
  } catch (error) {
    const err = error as Error;
    return new Response(`Error: ${err.message}\n${err.stack}`, {
      status: 500,
      headers: { "content-type": "text/plain" },
    });
  }
}
