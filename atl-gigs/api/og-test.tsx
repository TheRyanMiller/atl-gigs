import { ImageResponse } from "@vercel/og";

export const config = {
  runtime: "edge",
};

export default async function handler() {
  try {
    const response = new ImageResponse(
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
    return response;
  } catch (e: unknown) {
    const error = e as Error;
    return new Response(`Error: ${error.message}\n${error.stack}`, {
      status: 500,
      headers: { "Content-Type": "text/plain" },
    });
  }
}
