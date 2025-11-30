import { ImageResponse } from "@vercel/og";

export default async function handler() {
  try {
    const imageResponse = new ImageResponse(
      (
        <div
          style={{
            fontSize: 40,
            color: "black",
            background: "white",
            width: "100%",
            height: "100%",
            padding: "50px 200px",
            textAlign: "center",
            justifyContent: "center",
            alignItems: "center",
            display: "flex",
          }}
        >
          Hello Vercel
        </div>
      ),
      {
        width: 1200,
        height: 630,
      }
    );

    // Debug: get the array buffer to see if there's content
    const buffer = await imageResponse.arrayBuffer();
    const size = buffer.byteLength;

    if (size === 0) {
      return new Response(`DEBUG: ImageResponse created but buffer is empty (0 bytes)`, {
        status: 500,
        headers: { "Content-Type": "text/plain" },
      });
    }

    // Return a new response with the buffer
    return new Response(buffer, {
      status: 200,
      headers: {
        "Content-Type": "image/png",
        "Cache-Control": "public, max-age=31536000, immutable",
        "X-Image-Size": size.toString(),
      },
    });
  } catch (e: unknown) {
    const error = e as Error;
    return new Response(`Error: ${error.message}\n${error.stack}`, {
      status: 500,
      headers: { "Content-Type": "text/plain" },
    });
  }
}
