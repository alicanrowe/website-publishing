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
