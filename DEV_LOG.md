# Development Log — DocPortal Landing Page

## 2026-03-18

### `b691c74` improve conversion: better success message + book a call CTA
- Updated Hero waitlist success message to: "✓ You're on the list! Check your inbox — we'll be in touch within 24 hours with your free access."
- Added "Want faster access? Book a 15-min call →" link below the waitlist form (placeholder `#` link, styled as small gray underlined text)

### `79ec912` offer free early access for first 10 users
- **Pricing card**: changed "$29/month" → "Free for first 10 users"
- **Pricing card**: added "Get Free Early Access" button (scrolls to waitlist form)
- **Pricing card**: added subtext "After that, $29/month. Cancel anytime."
- **Pricing card**: updated trial badge to "No credit card required"
- **Hero form**: placeholder changed to "Enter your email for free access"
- **Hero form**: button text changed to "Get Free Access →"

### `703b06b` add landing page
- Initial single-file landing page (`index.html`)
- Sections: nav, hero with waitlist form, social proof quote, how-it-works feature grid, before/after comparison, pricing card, footer CTA, footer
- Formspree integration for email collection
- Responsive design with mobile breakpoints
