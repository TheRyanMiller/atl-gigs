import { ImageResponse } from "@vercel/og";
import type { VercelRequest, VercelResponse } from "@vercel/node";

export default async function handler(req: VercelRequest, res: VercelResponse) {
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

  const buffer = await imageResponse.arrayBuffer();
  res.setHeader("Content-Type", "image/png");
  res.setHeader("Cache-Control", "public, max-age=31536000, immutable");
  res.send(Buffer.from(buffer));
}
