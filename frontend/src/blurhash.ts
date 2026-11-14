/** BlurHash decoder for the picture placeholders (G3 stores the hash, backend/app/imagemeta.py encodes it). */
const B83 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%*+,-.:;=?@[]^_{|}~';

const read83 = (text: string) => {
  let value = 0;
  for (const c of text) {
    const digit = B83.indexOf(c);
    if (digit < 0) return -1;
    value = value * 83 + digit;
  }
  return value;
};
const toLinear = (v: number) => { const x = v / 255; return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; };
const toSrgb = (v: number) => { const x = Math.max(0, Math.min(1, v)); return Math.round((x <= 0.0031308 ? x * 12.92 : 1.055 * x ** (1 / 2.4) - 0.055) * 255); };
const signPow = (v: number, e: number) => Math.sign(v) * Math.abs(v) ** e;

/** RGBA pixels of a width × height picture, or null when the hash is not a valid BlurHash. */
export function decodeBlurhash(hash: string, width: number, height: number): Uint8ClampedArray | null {
  if (!hash || hash.length < 6) return null;
  const size = read83(hash[0]);
  const nx = (size % 9) + 1, ny = Math.floor(size / 9) + 1;
  if (size < 0 || hash.length !== 4 + 2 * nx * ny) return null;
  const maxAc = (read83(hash[1]) + 1) / 166;
  const dc = read83(hash.slice(2, 6));
  if (maxAc <= 0 || dc < 0) return null;
  const colors: number[][] = [[toLinear(dc >> 16), toLinear((dc >> 8) & 255), toLinear(dc & 255)]];
  for (let i = 1; i < nx * ny; i++) {
    const v = read83(hash.slice(4 + i * 2, 6 + i * 2));
    if (v < 0) return null;
    colors.push([Math.floor(v / 361), Math.floor(v / 19) % 19, v % 19].map(q => signPow((q - 9) / 9, 2) * maxAc));
  }
  const pixels = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let r = 0, g = 0, b = 0;
      for (let j = 0; j < ny; j++) {
        for (let i = 0; i < nx; i++) {
          const basis = Math.cos((Math.PI * x * i) / width) * Math.cos((Math.PI * y * j) / height);
          const c = colors[i + j * nx];
          r += c[0] * basis; g += c[1] * basis; b += c[2] * basis;
        }
      }
      const at = 4 * (x + y * width);
      pixels[at] = toSrgb(r); pixels[at + 1] = toSrgb(g); pixels[at + 2] = toSrgb(b); pixels[at + 3] = 255;
    }
  }
  return pixels;
}
