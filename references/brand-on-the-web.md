# The brand on the site

The full theme lives in the brand folder (`THEME.md`, `theme.json`, `theme.css`, fonts, `logo.svg`). Read `THEME.md` there before designing anything new. `site.css` already carries the same tokens as `--ar-*` variables; use those on pages.

## The look
A white page with a lot of empty space. Light, thin serif (Newsreader 200 and 300 only, never bold). Uppercase for nav, titles and labels; sentence case for body. Soft grey ink, not pure black. IBM Plex Mono only for small factual lines: dimensions, spec tables, captions, credits, footer. Media runs almost edge to edge with thin, even gaps. No boxes, cards, borders around content, shadows, rounded corners, gradients or filled buttons. Motion is slow fades and hairline draws, never slides or bounces.

| Role | Type | Colour |
|---|---|---|
| Page title | Newsreader 300, 21.23px, uppercase, .013em | `rgba(0,0,0,.68)` |
| Body | Newsreader 200, 13.27 / 19.24px | `--ar-ink` `rgba(0,0,0,.75)` |
| Name label under an image | Newsreader 200, 13px, uppercase | `#000` |
| Spec line, caption, table | Plex Mono 400, 10.5 to 11.5px | `--ar-ink`, labels `rgba(0,0,0,.5)` |
| Nav | Newsreader 300, 21px, uppercase | `--ar-nav` `rgba(71,37,37,.68)` |

Gaps: 12px between columns, 20px between rows, 6px in galleries. Text columns max 526px (notes) or 700px (intro), never full width. Empty image slots `#F3F3F3`. Links underlined with a 2px offset, same colour as the text. Phone: one column, 23px gutters, same type sizes (drawings may scale their labels up so they stay readable).

## The current page look (the Nine Lives sheet)
New and reworked project pages follow `content/nine-lives.md`: a left-aligned column up to 1240px, the title in Newsreader 300 caps (21.23px), the subtitle as plain body text (not grey tracked caps), a 0.5px hairline between sections, numbers, kickers and facts in Plex Mono 11.5px, captions in 11px caps, and no boxed cards. Older pages that were centred with grey tracked subtitles and bordered cards read as outdated; the robot project and The Dancers were brought over with the site repo's `static/assets/lc-sheet.css`, Info was rebuilt. A page passing `theme_audit.mjs` can still look old: compare it side by side with Nine Lives at both widths.

## One header on every page
The home page is a raw page with its own header, so it drifts from the shared header in `site.css` / `site.json` unless both are changed together. Same nav labels, order, size and colour, same logo position, on desktop and in the phone menu. The layout is the home page's: work nav (Sculpture, Furniture, Robotics, AI) on the left, the logo centred, studio nav (Mandelbulbs, Info, Commissions) on the right; on phones the logo on the left and a burger on the right. In `site.json` each nav item has `side: left|right`. `theme_audit.mjs` fails any page whose nav words sit more than 1% of the width away from where they sit on the home page, or whose header type differs from the rest.

## Weights
`site.css` maps any Newsreader weight from 251 to 900 onto the 300 cut, so `<strong>`, `<b>` or `font-weight:400` still draw the light face rather than a fake bold. Still write 200 or 300 in page styles; the audit warns on 400+.

## Accent colour
Grey ink only for text, numbers, labels and links. The dark red `#96281c` belongs to dimensions on drawings (SVG text and dimension lines), not to step numbers, section labels or "view on" links in the page text.

## Never on the site
- No custom page themes. The old moth theme (near-black, warm white, terracotta, script and blackletter titles, dark header) was retired on 19 Nov 2026; the Moth page uses the site theme like every other page.
- Plex Mono as body text; Jost; weight 400+ Newsreader.
- Text on plates, scrims or boxes.
- Firebrick red as a general accent. It appears once: the home page plumb line and GRAVITY / GRACE turning red when the line comes to rest.

## Words over photos
- White Newsreader 300, at least 12 to 13px, with a soft dark edge (a tight and a wide blurred dark copy behind it), never a hard light outline or halo. On the plain cyc, plain ink with no effect. Check legibility over the brightest and the busiest part of the image, and in every colour state the words can take.

## Drawings and diagrams on the site
- Inline SVG, so text stays sharp and can use the site fonts: labels in Plex Mono, dimensions in a single dark red (`#96281c` on the moth drawings) with small filled arrowheads, hairline extension lines.
- Fill parts in the materials' own light tones or `--ar-image-fill`, outlines in dark grey, never pure black blocks.
- Every drawing gets `role="img"` and an `aria-label` that says what it shows.
- Check label size at 390 wide. If labels drop under about 9px on phone, raise the font size for phone in a media query (mouthpad's `.mp-big`).
