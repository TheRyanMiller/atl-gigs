export const config = {
  runtime: "edge",
};

export default async function handler() {
  try {
    const wasmModule = new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0]); // minimal valid WASM header
    const validated = typeof WebAssembly !== "undefined" ? WebAssembly.validate(wasmModule) : false;
    const instantiated = await WebAssembly.instantiate(wasmModule);

    return new Response(
      JSON.stringify(
        {
          ok: true,
          wasmAvailable: typeof WebAssembly !== "undefined",
          validated,
          instanceExports: Object.keys(instantiated.instance.exports || {}),
        },
        null,
        2
      ),
      {
        status: 200,
        headers: { "content-type": "application/json" },
      }
    );
  } catch (error) {
    const err = error as Error;
    return new Response(
      JSON.stringify(
        {
          ok: false,
          message: err.message,
          stack: err.stack,
        },
        null,
        2
      ),
      {
        status: 500,
        headers: { "content-type": "application/json" },
      }
    );
  }
}
