# Cuts the dark background off sticker images and saves transparent PNGs.
# Works because each character has a white die-cut border: dark pixels connected to the image edge are background.
#   .\scripts\cutout.ps1 -Dir kaynak\referans\koala-progress-bw-2 -Filter 'q*.png'
param(
  [Parameter(Mandatory)][string]$Dir,
  [string]$Filter = '*.png',
  [string]$Out = '',
  [int]$Threshold = 110, # luminance below this counts as background
  [switch]$EraseEdgeLine, # also erase the thin horizontal "ledge" line the model draws beside peeking paws
  [switch]$Trim # crop to the visible content
)

Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
public static class Cut {
  public static void Run(string src, string dst, int thr) {
    using (var b0 = new Bitmap(src)) {
      int w = b0.Width, h = b0.Height;
      var bmp = new Bitmap(w, h, PixelFormat.Format32bppArgb);
      using (var g = Graphics.FromImage(bmp)) g.DrawImage(b0, 0, 0, w, h);
      var d = bmp.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);
      int stride = d.Stride;
      byte[] px = new byte[stride * h];
      Marshal.Copy(d.Scan0, px, 0, px.Length);
      var seen = new bool[w * h];
      var q = new Queue<int>();
      Func<int, bool> dark = i => {
        int o = (i / w) * stride + (i % w) * 4;
        return (px[o] * 114 + px[o + 1] * 587 + px[o + 2] * 299) / 1000 < thr;
      };
      for (int x = 0; x < w; x++) { Seed(x, seen, q, dark); Seed((h - 1) * w + x, seen, q, dark); }
      for (int y = 0; y < h; y++) { Seed(y * w, seen, q, dark); Seed(y * w + w - 1, seen, q, dark); }
      while (q.Count > 0) {
        int i = q.Dequeue(); int x = i % w, y = i / w;
        if (x > 0) Seed(i - 1, seen, q, dark);
        if (x < w - 1) Seed(i + 1, seen, q, dark);
        if (y > 0) Seed(i - w, seen, q, dark);
        if (y < h - 1) Seed(i + w, seen, q, dark);
      }
      for (int i = 0; i < seen.Length; i++) if (seen[i]) px[(i / w) * stride + (i % w) * 4 + 3] = 0;
      Marshal.Copy(px, 0, d.Scan0, px.Length);
      bmp.UnlockBits(d);
      bmp.Save(dst, ImageFormat.Png);
      bmp.Dispose();
    }
  }
  static void Seed(int i, bool[] seen, Queue<int> q, Func<int, bool> dark) {
    if (!seen[i] && dark(i)) { seen[i] = true; q.Enqueue(i); }
  }
}
'@

# .NET resolves relative paths against its own working directory, not PowerShell's, so use absolute ones.
$Dir = (Resolve-Path $Dir).Path
if ($Out -eq '') { $Out = Join-Path $Dir 'kes' }
elseif (-not [System.IO.Path]::IsPathRooted($Out)) { $Out = Join-Path (Get-Location).Path $Out }
New-Item -ItemType Directory -Force $Out | Out-Null
$files = Get-ChildItem $Dir -Filter $Filter -File
foreach ($f in $files) {
  $dst = Join-Path $Out ($f.BaseName + '.png')
  [Cut]::Run($f.FullName, $dst, $Threshold)
  if (-not ($EraseEdgeLine -or $Trim)) { continue }

  $bmp = New-Object System.Drawing.Bitmap $dst
  $w = $bmp.Width; $h = $bmp.Height
  if ($EraseEdgeLine) {
    # the line starts at the far-left column: first opaque row there is the line row
    $ly = -1
    for ($y = [int]($h * 0.3); $y -lt [int]($h * 0.9); $y++) { if ($bmp.GetPixel(3, $y).A -gt 40) { $ly = $y; break } }
    if ($ly -gt 0) {
      $none = [System.Drawing.Color]::FromArgb(0, 0, 0, 0)
      # a line pixel has nothing opaque 14 px above or below it; character pixels do
      for ($y = $ly - 8; $y -le $ly + 10; $y++) { for ($x = 0; $x -lt $w; $x++) {
        if ($bmp.GetPixel($x, $y).A -gt 0 -and $bmp.GetPixel($x, $y - 14).A -eq 0 -and $bmp.GetPixel($x, $y + 14).A -eq 0) { $bmp.SetPixel($x, $y, $none) } } }
    }
  }
  if ($Trim) {
    $x0 = $w; $y0 = $h; $x1 = -1; $y1 = -1
    for ($y = 0; $y -lt $h; $y += 2) { for ($x = 0; $x -lt $w; $x += 2) { if ($bmp.GetPixel($x, $y).A -gt 8) { if ($x -lt $x0) { $x0 = $x }; if ($x -gt $x1) { $x1 = $x }; if ($y -lt $y0) { $y0 = $y }; if ($y -gt $y1) { $y1 = $y } } } }
    if ($x1 -ge $x0) { $r = New-Object System.Drawing.Rectangle $x0, $y0, ($x1 - $x0 + 1), ($y1 - $y0 + 1); $c = $bmp.Clone($r, $bmp.PixelFormat); $bmp.Dispose(); $bmp = $c }
  }
  $tmp = "$dst.tmp"; $bmp.Save($tmp, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose(); Move-Item -Force $tmp $dst
}
Write-Host "kesilen: $($files.Count) -> $Out"
