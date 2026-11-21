# Project cards

Any page that lists projects (home, the category pages, /digital) uses the home page's card, so a project looks the same wherever it is listed. the owner asked for this after the AI page showed 4:3 tiles with three caption lines next to the home page's 4:5 cards.

- A 4:5 window on the cyc (`#ecebe7`), the image `object-fit: cover`, then a caption row: the name in Newsreader 300 11px caps on the left, one short fact in Plex Mono 10.5px on the right (`vibe CAD`, `claude skill`, `digital render`). Phone: two across, the fact under the name.
- Hairlines between cards (1px outline at 6% black), no boxes or gaps; the grid runs edge to edge, four across on desktop.
- On normal pages: `<div class="ar-cards">` with `<a class="ar-card" href><span class="ar-win"><img …></span><span class="ar-cap"><span class="ar-name">…</span><span class="ar-fact">…</span></span></a>`. `%% portfolio %%` builds the same cards; a spec line `crop: 65% 50%` moves the image in its window.
- A project with a model gets it in the card, turning, as on the home page: `<div class="ar-card"><div class="ar-win ar3d" data-src="….glb" data-spin="slow" data-orbit="30deg 72deg 2.4m" data-maxorbit="auto auto 6m"><div class="ar3d-stage"></div></div><a class="ar-cap" href>…</a></div>` plus `viewer.js`. Without `data-maxorbit` the radius is clamped to model-viewer's own framing and the model fills the card. A model whose bounds include empty space (the robot project) needs `data-target`.
- Crop on the subject: for a wide or square image in a 4:5 window only the horizontal position moves. Find the focal point (x as a fraction of the width), then `object-position` = (x − w/2) ÷ (1 − w) where w is the share of the width the window shows. Check it in the screenshot.
- `lint_page.py` errors on the older tile styles (`rb-grid`, `ar-cell`, `ar-tile`, `ar-portfolio`).

# Render, 3D viewer and drawing inline, with the spec table

A piece with a model is shown as one block: the render, the live 3D model and the dimension drawing side by side, then a short text and the spec table under them. A visitor reads the three together: what it looks like, how it turns, how big it is. `templates/project-page.md` has this layout ready to fill in.

## Layout rules
- **Side by side, not in separate sections.** Viewer and drawing belong in the same row. On the Moth page they were first two sections apart, and the drawing was never looked at next to the model.
- **Three across from 1100 px**, render full width above viewer + drawing from 768 to 1099 px, one column on phones (render, viewer, drawing, then text and spec table).
- **One square frame for all three**, so tops, bottoms and captions line up. Media is centred in its frame and never cropped. A very tall or wide piece can use another ratio, the same for all three.
- **Captions** in Plex Mono 10.5px uppercase, centred under each frame: `Render`, `In 3D · Drag to turn`, `Dimensions, inches`.
- **The 3D stage background is white**, same as the page; no grey box behind the model.
- **Spec table** to the right of the text on wide screens, under it on phones. Plex Mono 11px, labels at 50% black, a single hairline above, no other rules or boxes.
- Twelve px between columns; space from empty area, not padding.

## Drawing
- Inline `<svg>` with `role="img"` and an `aria-label`; never a raster screenshot of a drawing.
- **Size labels for the size the drawing is shown at.** An SVG with an 860-unit-wide viewBox shown 460 px wide scales everything by 0.53, so 15-unit text comes out at 8 px. Font size in viewBox units = target px × viewBox width ÷ shown width. Aim for 11 to 13 px on desktop and at least 9 px on a 390 px phone.
- Dimensions in one dark red with small filled arrowheads, labels in Plex Mono, parts in the material's light tone with a dark grey outline.
- Draw it from the same model file and version as the viewer GLB and the render. Put the version (and hash, for furniture) in the spec table.

## Spec table
Read it off the current cut list or model, never from memory. Typical rows: overall size, material (species and cut for wood), joinery or mechanism, hardware (maker and model), finish, weight if known, model version. For a work in progress, say what's still open.

## Before publishing
Compare the three against each other and the model: same parts, same proportions, same version. A viewer that still shows removed parts is the most common miss. Furniture pieces also follow the CAD skill's own checks first (hardwood-furniture-cad: model checked and design locked before final renders).

## Variant images as viewer buttons (seasons, stones, finishes)
When a piece comes in variants (the jewelry line's four seasons) and the page shows one still per variant beside the 3D viewer, the stills are the switch: clicking one loads that variant in the viewer.
- Wrap each still in `<figure class="mb-fig"><button type="button" class="mb-pick" data-pick="<viewer id>" data-src="<variant glb>" data-name="<Piece, variant>" aria-pressed="true|false" aria-label="Show <Piece, variant> in 3D"><img … alt=""><span class="mb-cap">Variant</span></button></figure>`. `viewer.js` already handles any `[data-pick]` element, so no new script for the swap; the image's alt is empty because the button's label names it.
- Keep the short word list under the viewer too (`.ar3d-pick`): on a phone the stills stack below the viewer. `viewer.js` presses every control for the same viewer that has the same `data-src`, so the words and the stills stay in step.
- Active state on brand: no boxes, borders or fills. The active still is full strength with its caption underlined (.5px, 3px offset); the others sit at 50% opacity (60% on touch screens), fading in over .6s on hover. A .5px outline shows only on `:focus-visible` for keyboard users.
- A tap on a still whose viewer is off screen scrolls the viewer back into view (smooth, or instant under reduced motion); it's a small inline script on the page.
- No angle strip under it. Once a piece has a viewer, don't add a row of static angle or orthographic views of the same piece (the jewelry line had three "view 1/2/3" stills under each ring and the cuff; the owner called them redundant and they were removed). `lint_page.py` errors on them.
- Check: click, Tab+Enter, Space and a phone tap each change the viewer's model and caption and press the matching word and still.
