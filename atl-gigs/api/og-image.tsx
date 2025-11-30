import { ImageResponse } from "@vercel/og";

export const config = {
  runtime: "edge",
};

export default async function handler(request: Request) {
  const { searchParams } = new URL(request.url);
  const imageUrl = searchParams.get("image");
  const date = searchParams.get("date"); // YYYY-MM-DD

  // If no image or date provided, return error
  if (!imageUrl || !date) {
    return new Response("Missing required parameters", { status: 400 });
  }

  // Parse date
  const eventDate = new Date(date + "T12:00:00");
  const day = eventDate.getDate();
  const month = eventDate
    .toLocaleDateString("en-US", { month: "short" })
    .toUpperCase();

  // Fetch the external image and convert to base64 data URL
  let imageData: string;
  try {
    const imageResponse = await fetch(imageUrl);
    if (!imageResponse.ok) {
      throw new Error(`Failed to fetch image: ${imageResponse.status}`);
    }
    const arrayBuffer = await imageResponse.arrayBuffer();
    // Convert ArrayBuffer to base64 using web APIs (edge runtime compatible)
    const bytes = new Uint8Array(arrayBuffer);
    let binary = "";
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    const base64 = btoa(binary);
    const contentType = imageResponse.headers.get("content-type") || "image/jpeg";
    imageData = `data:${contentType};base64,${base64}`;
  } catch (error) {
    console.error("Error fetching image:", error);
    // Return a simple fallback without the background image
    return new ImageResponse(
      (
        <div
          style={{
            display: "flex",
            width: "100%",
            height: "100%",
            backgroundColor: "#171717",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span style={{ fontSize: 48, color: "white", fontWeight: 700 }}>
            ATL
          </span>
          <span style={{ fontSize: 48, color: "#14b8a6", fontWeight: 700 }}>
            Gigs
          </span>
        </div>
      ),
      { width: 1200, height: 630 }
    );
  }

  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          width: "100%",
          height: "100%",
          position: "relative",
        }}
      >
        {/* Background event image */}
        <img
          src={imageData}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />

        {/* Dark gradient overlay for contrast */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              "linear-gradient(to top, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.2) 30%, transparent 60%)",
          }}
        />

        {/* Date badge - top left */}
        <div
          style={{
            position: "absolute",
            top: 32,
            left: 32,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(10,10,10,0.85)",
            borderRadius: 20,
            padding: "16px 28px",
            border: "1px solid rgba(255,255,255,0.15)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
          }}
        >
          <span
            style={{
              fontSize: 18,
              color: "#2dd4bf",
              fontWeight: 700,
              letterSpacing: "0.05em",
            }}
          >
            {month}
          </span>
          <span
            style={{
              fontSize: 48,
              color: "white",
              fontWeight: 700,
              lineHeight: 1,
            }}
          >
            {day}
          </span>
        </div>

        {/* ATL Gigs logo - bottom right */}
        <div
          style={{
            position: "absolute",
            bottom: 32,
            right: 32,
            display: "flex",
            alignItems: "center",
            gap: 10,
            background: "rgba(10,10,10,0.85)",
            borderRadius: 16,
            padding: "12px 24px",
            border: "1px solid rgba(255,255,255,0.15)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
          }}
        >
          <span style={{ fontSize: 28, color: "white", fontWeight: 700 }}>
            ATL
          </span>
          <span style={{ fontSize: 28, color: "#14b8a6", fontWeight: 700 }}>
            Gigs
          </span>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
