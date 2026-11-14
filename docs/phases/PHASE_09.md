# PHASE 9: The app front end (REVIEW PACK)

**Date:** 2026-11-14 | **Status:** Committed under the standing instruction "complete all the phases" (change requests welcome).

```
PHASE: 9, a plain-language web page for pond owners (plain HTML, CSS and JavaScript; no libraries)
DELIVERED: app/static/{index.html,style.css,app.js}
DESIGN RULES: no jargon on screen; every input is a named key with an example value; every number has a "how did we get this?" in everyday words;
              the page never says what "caused" anything; nothing is stored; text is inserted with textContent only (no innerHTML)
CHECKED: screenshots in a real browser at desktop width (the full flow: example, results, charts, ranges, risk meters); unit test that app.js never uses innerHTML/eval
```

## What a pond owner sees
1. **Tell us about your pond:** *Pond name*; *Your readings* by pasting from a spreadsheet, uploading a file, or **Try an example** (made-up numbers, clearly labelled); a "What do I need to give?" box of key/value pairs:
   **Time**, **Oxygen**, **pH**, **Temperature**, **How much** (at least 25 hours, ideally every 15 minutes), each with an example; a blank template to download.
2. **What we found in your readings:** key/value pairs (*Readings used, Time covered, First reading, Latest reading, Readings missing in between*) and plain notes (for example "3 oxygen readings were exactly 0. A sensor often shows 0 when it is not working, so we ignored them").
3. **What we expect:** *Right now* values; **Chance of very low oxygen** (marked *Experimental*) for the next hour, 3 hours and 6 hours with a bar and a word (Low / Some / High chance); then **Oxygen, Acidity (pH), Water temperature** cards with a chart (last 24 hours as a line, expected values as dots with bars), and for 15 minutes, 1 hour and 6 hours ahead: "About 5.1 mg/L, likely between 3.8 mg/L and 6.5 mg/L", a range bar, and **How did we get this?** (which method was used, how it did in testing, the three biggest reasons in sentences).
4. **How much can I trust this?** and **Things to keep in mind**, plus a glossary ("What is dissolved oxygen?", "What does likely between mean?", "What is a plain guess?").

## Honesty built into the wording
- When a trained model did not beat a plain guess (pH at every distance, temperature at 15 minutes), the card says "We simply repeated the latest reading" or "We used the reading from the same time yesterday", and why.
- Explanations that did not pass the Phase 8 stability tests (oxygen 15 minutes) are shown with "treat them as a rough guide only".
- The alert is badged *Experimental*; a banner and the footer say it is a research demonstration that does not replace sensors or alarms.
- Words like "safe" or "dangerous" are not used.

## Accessibility and layout
Large base font, strong contrast, light and dark colour schemes, keyboard focus outlines, a skip link, labelled tabs, charts with a text description, a single-column layout on phones.

## Decisions I need
Approve the wording and layout, or tell me what a pond owner would find confusing.
