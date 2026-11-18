# The brand on the site

The full theme lives in the brand folder (`THEME.md`, `theme.json`, `theme.css`, fonts, `logo.svg`). In alican's project it is mirrored at `/mnt/project-files/brand/`. Read `THEME.md` there before designing anything new. `site.css` already carries the same tokens as `--ar-*` variables; use those on pages.

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

## Never on the site
- The moth custom theme (near-black, warm white, terracotta, blackletter). It belongs to the moth case's own material, not the site shell. Pages may use it inside their own section only when alican asks.
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
