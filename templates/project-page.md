---
title: "piece name"
url: "/piece-name"
nav: "core studio furniture"
description: "One sentence: what the piece is, the material, what's special about it."
draft: true
---

%% html %%
<style>
/* pp- = this page's prefix. Replace it with a short prefix of your own (2 to 3 letters + dash). */
.pp-intro{max-width:700px;margin:clamp(24px,3vw,40px) auto clamp(28px,3.5vw,44px)}
.pp-intro h1{margin:0 0 14px;font:300 21.23px/1.6 var(--ar-serif);letter-spacing:.013em;text-transform:uppercase;color:rgba(0,0,0,.68);text-align:center}
.pp-intro p{margin:0 0 12px;font:200 13.27px/19.24px var(--ar-serif);letter-spacing:.021em;color:var(--ar-ink)}
.pp-h{margin:0 0 14px;text-align:center;font:300 21.23px/1.6 var(--ar-serif);letter-spacing:.013em;text-transform:uppercase;color:rgba(0,0,0,.68)}
/* render | 3D viewer | dimension drawing, side by side */
.pp-trio{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;align-items:start;max-width:1600px;margin:0 auto}
/* all three share one square frame so their tops, bottoms and captions line up */
.pp-trio figure{margin:0}
.pp-trio .pp-media{aspect-ratio:1/1;display:flex;align-items:center;justify-content:center}
.pp-trio .pp-media img,.pp-trio .pp-media svg{display:block;max-width:100%;max-height:100%;width:auto;height:auto}
.pp-trio .pp-media svg{width:100%}
.pp-trio .ar3d{max-width:none;margin:0}
.pp-trio .ar3d-stage{height:auto;aspect-ratio:1/1;background:#fff}
.pp-cap,.pp-trio .ar3d-cap{margin-top:8px;padding:0;text-align:center;font:400 10.5px/1.5 var(--ar-mono);letter-spacing:.08em;text-transform:uppercase;color:rgba(0,0,0,.5)}
.pp-trio .ar3d-cap{display:flex;justify-content:center;gap:1.4em}
/* text | spec table, under the trio */
.pp-about{display:grid;grid-template-columns:minmax(0,526px) minmax(0,420px);gap:12px 48px;justify-content:center;margin:clamp(28px,3.5vw,48px) auto clamp(40px,5vw,72px)}
.pp-about p{margin:0 0 12px;font:200 13.27px/19.24px var(--ar-serif);letter-spacing:.021em;color:var(--ar-ink)}
.pp-spec{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:6px 18px;margin:0;padding-top:10px;border-top:.5px solid rgba(0,0,0,.25);font:400 11px/1.5 var(--ar-mono);align-content:start}
.pp-spec dt{color:rgba(0,0,0,.5)}
.pp-spec dd{margin:0;color:var(--ar-ink)}
@media (max-width:1099px){.pp-trio{grid-template-columns:repeat(2,minmax(0,1fr))}.pp-trio .pp-render{grid-column:1/-1}}
@media (max-width:767px){.pp-trio{grid-template-columns:minmax(0,1fr);gap:28px}.pp-about{grid-template-columns:minmax(0,1fr);gap:20px}}
</style>
<script src="/assets/viewer.js" defer></script>

<section class="pp-intro">
<h1>Piece name</h1>
<p>Two or three sentences: what it is, what it's made of, how it works. Plain words, sentence case.</p>
</section>

<section class="pp-trio" aria-label="The piece: render, 3D model and dimensions">
<figure class="pp-render"><div class="pp-media"><img src="img/piece-name/piece-name-hero.jpg" alt="The finished piece in a full-colour render" width="1600" height="2000" loading="lazy" decoding="async"></div><figcaption class="pp-cap">Render</figcaption></figure>
<div class="ar3d pp-3d" data-src="/3d/piece-name/piece-name.glb" data-orbit="35deg 75deg auto" data-spin="slow" data-alt="The piece in 3D"><div class="ar3d-stage"></div><div class="ar3d-cap"><span class="ar3d-name">In 3D</span><span>Drag to turn</span></div></div>
<figure class="pp-dwg"><div class="pp-media"><!-- paste the drawing as inline <svg viewBox=… role="img" aria-label="…"> so its labels use the site fonts; see inline-layout.md for label sizes --></div><figcaption class="pp-cap">Dimensions, inches</figcaption></figure>
</section>

<section class="pp-about">
<div><p>What it's for, how it's built, the joinery or the mechanism. Keep it to a few short paragraphs.</p></div>
<dl class="pp-spec">
<dt>Overall</dt><dd>W × D × H in</dd>
<dt>Wood</dt><dd>species, cut</dd>
<dt>Joinery</dt><dd>…</dd>
<dt>Hardware</dt><dd>maker and model</dd>
<dt>Finish</dt><dd>…</dd>
<dt>Model</dt><dd>version and file hash</dd>
</dl>
</section>
