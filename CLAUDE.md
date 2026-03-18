# DocPortal Landing Page

## Project Overview
DocPortal is a client-facing document upload portal for solo bookkeepers. This repo contains the landing page (single `index.html`) used to collect waitlist signups.

## Tech Stack
- Single-file HTML landing page (no build tools, no framework)
- Fonts: Lora (serif headings) + DM Sans (body)
- CSS: vanilla CSS with CSS custom properties (`:root` variables)
- JS: vanilla JS, form submission via Formspree (`https://formspree.io/f/xgonpwez`)
- Hosting: GitHub Pages (repo: `captainpan007/docportal-landing`)

## File Structure
```
index.html   — entire landing page (HTML + CSS + JS inline)
```

## Page Sections (in order)
1. **Nav** — logo + CTA link
2. **Hero** — headline, subtitle, email waitlist form, success message, "book a call" link
3. **Social proof quote** — Reddit testimonial
4. **How it works** — 3-feature grid (link, dashboard, reminders)
5. **Before vs After** — comparison cards
6. **Pricing** — free for first 10 users, then $29/month
7. **Footer CTA** — second email capture form
8. **Footer** — copyright

## Design Tokens
- Green palette: `--green-50` through `--green-800`
- Gray palette: `--gray-50` through `--gray-800`
- Border radius: `--radius-sm` (6px), `--radius-md` (10px), `--radius-lg` (14px)

## Conventions
- All styles are inline in `<style>` within `<head>`
- All JS is inline in `<script>` before `</body>`
- Keep everything in a single file — do not split into separate CSS/JS files
- Maintain the existing visual style when making changes
