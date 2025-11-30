import { ImageResponse } from "@vercel/og";

export const config = {
  runtime: "edge",
};

export default async function handler(request: Request) {
  const { searchParams } = new URL(request.url);
  const imageUrl = searchParams.get("image");
  const date = searchParams.get("date");

  // Default/homepage OG image (no params)
  if (!imageUrl || !date) {
    return new ImageResponse(
      (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            width: "100%",
            height: "100%",
            backgroundColor: "#0a0a0a",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", marginBottom: 24 }}>
            <div
              style={{
                width: 80,
                height: 80,
                backgroundColor: "#0d9488",
                borderRadius: 20,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginRight: 16,
              }}
            >
              <span style={{ fontSize: 40, color: "white" }}>♪</span>
            </div>
            <span style={{ fontSize: 72, color: "white", fontWeight: 700 }}>ATL</span>
            <span style={{ fontSize: 72, color: "#14b8a6", fontWeight: 700, marginLeft: 12 }}>Gigs</span>
          </div>
          <span style={{ fontSize: 28, color: "#a3a3a3" }}>Live Music Events in Atlanta</span>
        </div>
      ),
      { width: 1200, height: 630 }
    );
  }

  // Parse date for event image
  const eventDate = new Date(date + "T12:00:00");
  const day = eventDate.getDate();
  const month = eventDate.toLocaleDateString("en-US", { month: "short" }).toUpperCase();

  // Fetch and encode the external image
  let imageData: string | null = null;
  try {
    const imageResponse = await fetch(imageUrl);
    if (imageResponse.ok) {
      const arrayBuffer = await imageResponse.arrayBuffer();
      const bytes = new Uint8Array(arrayBuffer);
      let binary = "";
      for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      const base64 = btoa(binary);
      const contentType = imageResponse.headers.get("content-type") || "image/jpeg";
      imageData = `data:${contentType};base64,${base64}`;
    }
  } catch (error) {
    console.error("Error fetching image:", error);
  }

  // Fallback if image fetch failed
  if (!imageData) {
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
          <span style={{ fontSize: 48, color: "white", fontWeight: 700 }}>ATL</span>
          <span style={{ fontSize: 48, color: "#14b8a6", fontWeight: 700, marginLeft: 8 }}>Gigs</span>
        </div>
      ),
      { width: 1200, height: 630 }
    );
  }

  // Event image with overlay
  return new ImageResponse(
    (
      <div style={{ display: "flex", width: "100%", height: "100%", position: "relative" }}>
        <img
          src={imageData}
          width={1200}
          height={630}
          style={{ objectFit: "cover" }}
        />
        {/* Date badge */}
        <div
          style={{
            position: "absolute",
            top: 32,
            left: 32,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            backgroundColor: "rgba(10,10,10,0.9)",
            borderRadius: 16,
            padding: "12px 24px",
          }}
        >
          <span style={{ fontSize: 16, color: "#2dd4bf", fontWeight: 700 }}>{month}</span>
          <span style={{ fontSize: 40, color: "white", fontWeight: 700 }}>{day}</span>
        </div>
        {/* Logo badge */}
        <div
          style={{
            position: "absolute",
            bottom: 32,
            right: 32,
            display: "flex",
            alignItems: "center",
            backgroundColor: "rgba(10,10,10,0.9)",
            borderRadius: 12,
            padding: "8px 16px",
          }}
        >
          <span style={{ fontSize: 24, color: "white", fontWeight: 700 }}>ATL</span>
          <span style={{ fontSize: 24, color: "#14b8a6", fontWeight: 700, marginLeft: 6 }}>Gigs</span>
        </div>
      </div>
    ),
    { width: 1200, height: 630 }
  );
}
