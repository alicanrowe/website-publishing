# Images, video and 3D for the site

## Images
- **2000 px wide maximum**, JPEG quality about 82, progressive. The build shrinks anything bigger, but the repo keeps the full file forever, so shrink before committing. Full-size originals live outside the repo (the owner's project keeps them under `site-static/_originals/`).
- **Renders** with an opaque background: save as JPEG, not PNG. The build turns opaque PNGs over 400 KB into JPEGs and rewrites the links, but a JPEG from the start is smaller and clearer. Keep PNG only for real transparency or line art.
- **Line drawings and diagrams:** inline SVG (inline-layout.md).
- Names lowercase with dashes, inside `content/img/<page>/`. Version in the name when it changes (`-v3`) so browsers don't show a cached old one.
- Every `<img>` has `alt` (what it shows, in a sentence), `width` and `height` (the file's pixel size, so the page doesn't jump), `loading="lazy"` and `decoding="async"`. The first image on a page (the hero) skips `loading="lazy"`.
- Images at least as wide as the column they sit in at 2x: a 900 px column wants an 1800 px image.

```
python3 - <<'PY'
from PIL import Image
im = Image.open('in.png').convert('RGB')
if im.width > 2000: im = im.resize((2000, round(im.height * 2000 / im.width)), Image.LANCZOS)
im.save('out.jpg', 'JPEG', quality=82, progressive=True, optimize=True)
print(im.size)
PY
```

## Other people's images
Use the largest original they publish, keep it unaltered, and credit it in a mono caption under the image with a link to their site (`Photo: <a href="…">Maker</a>`). Augmental's MouthPad photo on /mouthpad is the pattern. Ask the owner before using anything that isn't a public product or press image.

## Video
H.264 MP4, 1080p at most, about 15 MB or less, no audio track unless it's needed. `muted playsinline loop autoplay` for silent loops, with a `poster` JPEG. Over about 15 MB, re-encode (`ffmpeg -i in.mov -c:v libx264 -crf 24 -preset slow -an -movflags +faststart out.mp4`).

## 3D models (GLB)
- One GLB per viewer, under about 3 MB. Decimate in Blender first, remove hidden parts (fasteners inside, the back of things nobody sees), merge by material, then compress with meshopt: `gltfpack -i in.glb -o out.glb -cc` (the site vendors the meshopt decoder; don't use Draco or KTX2, the site doesn't load their decoders).
- Textures 2048 px maximum, JPEG or WebP inside the GLB.
- Materials the same as the renders, so the viewer and the render look like the same object.
- If any step rewrites the GLB with trimesh, put the material extensions back afterwards (transmission, ior, emissive strength; see lessons.md, 2026-11-19), or glass and clear plastic go opaque. Without gltfpack, `gltf-transform optimize in.glb out.glb --compress meshopt --texture-compress webp --texture-size 2048` gives the same result.
- Y up, metres, the model's base on the ground at the origin, so `data-orbit` defaults frame it well.
- Name them `<piece>-v<N>-lite.glb` and point the page at the new file; don't overwrite a file a live page uses.

## Embedded posts (Instagram, and any embed that sets its own width)
A set of embeds stays on one row, never 3 + 1. Instagram's `embed.js` swaps each blockquote for an iframe with a 326 px minimum width, so a flex row wraps. Use a grid and override the embed's own widths:
```html
<style>.k-reels{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;max-width:1400px;margin:10px auto 34px;align-items:start}
.k-reels>blockquote,.k-reels>iframe{min-width:0!important;max-width:none!important;width:100%!important;margin:0!important}
@media (max-width:900px){.k-reels{grid-template-columns:none;grid-auto-flow:column;grid-auto-columns:min(78%,326px);overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:6px}.k-reels>*{scroll-snap-align:start}}</style>
<div class="k-reels"><blockquote class="instagram-media" data-instgrm-permalink="..." data-instgrm-version="14" style="background:#fff;border:0;margin:0;padding:0;width:100%">...</blockquote>...</div>
```
Check it: every iframe in the row has the same top at 1440, and at 390 the row scrolls sideways without the page scrolling sideways.

