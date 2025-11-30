import { ImageResponse } from "@vercel/og";

export const config = {
  runtime: "edge",
};

// Fetch font from Google Fonts
const fontPromise = fetch(
  "https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_nVMrMxCp50SjIw2boKoduKmMEVuLyfAZ9hjp-Ek-_0ew.woff"
).then((res) => res.arrayBuffer());

export default async function handler() {
  const fontData = await fontPromise;

  return new ImageResponse(
    (
      <div
        style={{
          fontSize: 60,
          color: "white",
          background: "black",
          width: "100%",
          height: "100%",
          display: "flex",
          textAlign: "center",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "Inter",
        }}
      >
        Hello World
      </div>
    ),
    {
      width: 1200,
      height: 630,
      fonts: [
        {
          name: "Inter",
          data: fontData,
          style: "normal",
          weight: 400,
        },
      ],
    }
  );
}
