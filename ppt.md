# FATHOM — PITCH DECK

**Last build task. Execute top to bottom.**

Deliverable: `out/FATHOM_deck.pptx`

Read the pptx skill before starting.

---

## Format

- 16:9
- **Twelve slides maximum. Ten is better.** If a slide is not earning its place, cut it.
- Speaker notes on every slide: two or three sentences of what to say. Prompts, not a script.

---

## Design

Use FATHOM's own token system so the deck and the product read as one thing.

```
--abyss      #0B1620   page background
--deep       #12232F   panels
--shelf      #1C3644   hairlines, borders
--chart      #DDE6EA   primary text
--sounding   #6E8CA0   secondary text
--reached    #4FD1A5   a price returned
--obstructed #E8A33D   stopped at a known obstruction
--refused    #D9614C   access control, hard refusal
--unknown    #7C6BAD   unresolved
```

- Dark throughout.
- Status accents appear **only** where they carry meaning. Never as decoration.
- Headings: condensed, small caps with wide tracking where they act as instrument labels.
- **Every number, ID, hash, metric and status code in monospace.**
- No gradients. No stock imagery. No icon sets. No bullet clipart. No drop shadows.
- Border radius 2px maximum.
- Generous whitespace, big type. Readable from the back of a room.

---

## Wording

- Extremely plain language.
- No jargon on a slide without its plain-English equivalent beside it.
- **Maximum 25 words of body text per slide.** The screenshot carries the slide; the words caption it.
- Sentence case. No exclamation marks, no emoji, no filler.
- Active voice.

---

## Screenshots

Take these yourself. Load the UI in Chrome, capture at high resolution, crop tight to the relevant element.

**Verify no PII appears in any capture before embedding.** Check expanded rows and evidence previews specifically.

Needed:

1. The Sounding Chart, full width
2. The Market graph with the Aviva collapse highlighted
3. The Outcomes table with one row expanded showing coverage detail
4. The Gate log showing a real denial with its rule ID
5. The Eligibility Frontier
6. Terminal output of `make demo-fabrication` — the fabricated price, then the refusal
7. Optional: the Market view extraction panel (only if it fits slide 7 cleanly)

---

## Slide plan

Follow this order. Adjust wording as you see fit; do not add slides.

### 1 — Title

FATHOM. *Sound the market. Prove the bottom.*

One line on what it is.

### 2 — The problem

Three short lines, no more:

- Ontario has about 30 real insurers wearing about 100 names
- Since 1 July 2026, most accident benefits became optional, so two prices are rarely the same product
- Companies that refuse you vanish from every comparison tool

### 3 — What I built

One sentence plus the **Sounding Chart** screenshot. This is the hero slide; the image does the talking.

Caption explains the metaphor: every rate source is a sounding line, depth is how far the agent got, the marker is why it stopped.

### 4 — How it works

The pipeline as one simple diagram:

`intake → safety gate → route planner → executors → evidence chain → normalized results`

Emphasize visually that **everything** passes through the gate.

### 5 — Safety by construction

The gate is code, not prompting. 19 rules. It cannot buy, pay, sign, fake a licence, bypass a CAPTCHA, or mix two profiles.

Screenshot: the gate log showing a real denial with its rule ID.

One line: *the agent is not trusted to behave — it is prevented.*

### 6 — Untangling the market

70 brands → 67 distinct rate sources.

Screenshot: the Market graph with Aviva highlighted.

Caption: four Aviva brands are one legal entity since 1 January 2026, merged only on two independent evidenced signals.

### 7 — What the survey found

The honest result, stated confidently. Four findings:

1. No real route priced a hypothetical profile
2. Two comparison sites sit behind bot controls — detected and respected, not bypassed
3. Direct writers wall at a driver's licence number
4. The residual market publishes its rates publicly. FATHOM extracted 6,440 provenanced territory-definition rows from the current Facility Association Ontario manual, every row carrying its source page. The premium tables were too ambiguous to extract without guessing, so they were left out.

Label finding 4 **UNVERIFIED EXTRACTION** on the slide. State explicitly that no premium was computed and none is claimed. Do not call it a calculator or a rater — it is a structured extraction of territory definitions only. It is a supporting point, not a headline; give it no more room than the other three.

Close the slide: every outcome carries a timestamp, a reason code and evidence. Frame all four as findings, not failures.

If the extraction panel screenshot fits cleanly, include it small. If it crowds the slide, drop the screenshot and keep the text.

### 8 — The moment that matters

The fabricated price.

The executor reported `$177.83` as a quote. It was advertising copy on a landing page with zero fields submitted. Caught before it reached a report.

Screenshot: `make demo-fabrication`.

One line: *a system that returns numbers is not the same as a system that returns evidence.*

### 9 — From "no" to "next"

The Eligibility Frontier. Every refusal carries a reason; inverted, those reasons become a ladder of what unlocks what.

Screenshot.

**Be honest that it is currently thin — one real rung — and say why.**

### 10 — How AI did the work

Be specific, not generic:

- Agentic form navigation across multi-step insurer journeys, mapping each site's questions to one canonical schema
- Reading pages structurally rather than by brittle selectors, so layout changes don't break it
- Ask Your Findings: retrieval-gated question answering over its own evidence — it cites artifacts, and when the evidence doesn't contain the answer it refuses without calling the model at all
- **What AI deliberately does not do:** it never decides whether an action is permitted, and it never computes a number that gets reported. Those are deterministic code.

Give that last point visual emphasis. It is the interesting one.

### 11 — Tech stack

Compact and honest.

Python 3.12 · LangGraph · Playwright · FastMCP servers · SQLite + content-addressed evidence store · hash-chained audit log · local regex redaction · vanilla JS UI, no build step · Claude API for retrieval-gated answering.

Then: 161 tests passing, PII sweep clean across 207 files, two hash chains verifying intact.

### 12 — What I didn't build

List plainly: voice executor, rulebook compiler (premium calculation), benefit price probe, vehicle inversion, channel arbitrage, dark pattern detector.

Closing line: *a smaller number of trustworthy results with excellent evidence. Both the reach and the uncertainty are legible.*

---

## Rules

- **Every number on every slide must be true and traceable.** No rounding up, no "50+", no invented figures.
- Nothing may imply a real insurer returned a price.
- Sandbox-derived numbers labelled `SANDBOX` on the slide itself.
- No company is characterized as violating any law or rule anywhere in the deck.
- The extraction is never described as a price, a quote, a premium, a calculator or a rater.

---

## Before reporting done

1. Verify the file opens
2. Every screenshot embedded and legible at presentation size
3. No PII visible on any slide
4. Every figure cross-checked against `out/run_report.md`
5. Speaker notes present on all slides

Report in three lines.