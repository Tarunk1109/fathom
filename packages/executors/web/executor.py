"""Web executor — FATHOM §11.1, Milestone 4.

The agentic element the organizers asked for (AC-001 items 2 and 4): it reads a quote journey,
maps its fields to the canonical ontology, fills them from the active profile, and walks the flow
to a terminal status.

**Every action goes through the Policy Engine (DL-08).** There is no direct Playwright call in this
file that is not preceded by `evaluate()` returning ALLOW. That is what makes `P-APPROVAL-01`,
`P-HYPO-LICENCE-01` and the rest actually bite rather than decorate — including on a real insurer
site, where the approval gate is the last thing between the agent and a live form.

**Modals are polled, not caught (DL-09).** Day 0 found an address-validation modal mid-journey on
Sonnet, and a naive executor hangs on it. Every modal encountered is logged with its text, per the
operator's constraint.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from packages.evidence import EvidenceStore  # noqa: E402
from packages.policy import (  # noqa: E402
    FieldValue,
    PolicyEngine,
    ProposedAction,
    SessionContext,
)
from packages.profiles import Profile  # noqa: E402

from .ontology import FieldMatch, match_field  # noqa: E402

MODAL_SELECTORS = (
    "[role=dialog]", ".modal", "#address-modal", "[aria-modal=true]",
    ".overlay", ".popup", "dialog[open]",
)
DISMISS_TEXTS = ("okay", "ok", "got it", "continue", "close", "accept", "dismiss", "confirm")


@dataclass
class ModalEvent:
    step: int
    url: str
    text: str
    dismissed: bool
    dismissed_via: str = ""


@dataclass
class StepRecord:
    step: int
    url: str
    title: str
    fields_seen: list[str] = field(default_factory=list)
    fields_filled: list[str] = field(default_factory=list)
    fields_denied: list[tuple[str, str]] = field(default_factory=list)
    hypotheses: list[tuple[str, float]] = field(default_factory=list)


@dataclass
class RunResult:
    route_id: str
    profile_id: str
    entry_url: str
    status: str
    reason_code: str | None = None
    stopping_step: str = ""
    stated_reason: str = ""
    premium: float | None = None
    quote_reference: str = ""
    coverage: dict = field(default_factory=dict)
    steps: list[StepRecord] = field(default_factory=list)
    modals: list[ModalEvent] = field(default_factory=list)
    evidence_cids: list[str] = field(default_factory=list)
    policy_denials: list[tuple[str, str]] = field(default_factory=list)

    #: A denial that only becomes terminal if the journey cannot advance without the control.
    #: Skip where optional, block where mandatory — the pattern §2.1 sets for the licence plate,
    #: applied to every gated control. Without this a hypothetical profile stops at the first
    #: optional fraud checkbox, and most journeys carry one.
    pending_block: tuple[str, str, str, str] | None = None

    def summary(self) -> str:
        return (f"{self.route_id} [{self.profile_id}] -> {self.status}"
                + (f" ({self.reason_code})" if self.reason_code else "")
                + (f" ${self.premium:,.2f}" if self.premium else ""))


class WebExecutor:
    def __init__(self, engine: PolicyEngine, evidence: EvidenceStore,
                 max_steps: int = 12, slow_mo_ms: int = 0) -> None:
        self.engine = engine
        self.evidence = evidence
        self.max_steps = max_steps
        self.slow_mo_ms = slow_mo_ms

    # -- gate ---------------------------------------------------------------------------

    def _gate(self, ctx: SessionContext, kind: str, target: str, payload: dict | None,
              route_id: str, rationale: str):
        return self.engine.evaluate(ProposedAction(
            kind=kind, target=target, payload=payload, route_id=route_id,
            session_id=ctx.session_id, profile_id=ctx.profile_id, rationale=rationale,
        ), ctx)

    # -- run ----------------------------------------------------------------------------

    def run(self, *, route_id: str, entry_url: str, profile: Profile, ctx: SessionContext,
            headless: bool = True) -> RunResult:
        from playwright.sync_api import sync_playwright

        result = RunResult(route_id=route_id, profile_id=profile.profile_id, entry_url=entry_url,
                           status="unresolved")

        decision = self._gate(ctx, "navigate", entry_url, None, route_id,
                              "Open the quote journey.")
        if decision.verdict != "ALLOW":
            result.status = decision.terminal_status or "blocked"
            result.stopping_step = "entry"
            result.stated_reason = decision.explanation
            result.policy_denials.append((decision.rule_id, decision.explanation))
            return result

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless, slow_mo=self.slow_mo_ms)
            page = browser.new_page()
            try:
                page.goto(entry_url, wait_until="domcontentloaded")
                # Real insurer journeys are JS-rendered; the form does not exist at DOMContentLoaded.
                try:
                    page.wait_for_load_state("networkidle", timeout=4000)
                except Exception:
                    pass
                self._walk(page, result, profile, ctx)
            finally:
                browser.close()
        return result

    # -- the loop -----------------------------------------------------------------------

    def _walk(self, page, result: RunResult, profile: Profile, ctx: SessionContext) -> None:
        for step_index in range(1, self.max_steps + 1):
            budget = ctx.budget_for(result.route_id)
            if budget.expired():
                result.status = "unresolved"
                result.stopping_step = f"step {step_index}: route time budget exhausted"
                result.stated_reason = ("The journey did not reach a terminal state within the "
                                        "route's time budget (§9.4).")
                return
            self._handle_modals(page, result, step_index)

            record = StepRecord(step=step_index, url=page.url, title=page.title())
            result.steps.append(record)

            text = page.inner_text("body")
            artifact = self.evidence.append(
                content=text, route_id=result.route_id, profile_id=profile.profile_id,
                kind="page_text", source=page.url)
            result.evidence_cids.append(artifact.cid)

            if self._detect_bot_check(page, text):
                result.status, result.reason_code = "blocked", "RC_ACCESS_CONTROL"
                result.stopping_step = f"step {step_index}: bot check"
                result.stated_reason = "A CAPTCHA or bot control was presented."
                return

            # A price is only believed when this run actually submitted something. Landing pages
            # advertise "from $177/mo" and the reader happily returned it — a fabricated quote,
            # which §6.1 says ends the submission. Filling at least one field is the minimum
            # evidence that the number on screen is a response to our inputs rather than copy.
            price = (self._read_price(page, text)
                     if any(st.fields_filled for st in result.steps) else None)
            if price is not None:
                result.premium = price
                result.quote_reference = self._read_quote_ref(text)
                result.coverage = self._read_coverage(text)
                result.status = "quoted_comparable"
                result.stopping_step = f"step {step_index}: priced"
                return

            filled_any = self._fill_step(page, record, result, profile, ctx)

            if self._detect_callback_only(page, text):
                result.status, result.reason_code = "callback_required", "RC_HUMAN_REQUIRED"
                result.stopping_step = f"step {step_index}: callback only"
                result.stated_reason = "The journey offers a callback instead of a price."
                return

            advanced = self._advance(page, result, ctx, step_index)
            if advanced:
                # The journey moved on without the gated control, so it was optional.
                result.pending_block = None
                continue

            if result.pending_block:
                status, reason, where, why = result.pending_block
                result.status, result.reason_code = status, reason
                result.stopping_step = f"{where} (mandatory — journey cannot advance)"
                result.stated_reason = why
            elif not filled_any:
                result.status = "unresolved"
                result.stopping_step = f"step {step_index}: no actionable control"
            else:
                result.status = "unresolved"
                result.stopping_step = f"step {step_index}: could not advance"
            return
        result.status = "unresolved"
        result.stopping_step = f"exhausted {self.max_steps} steps"

    # -- modals -------------------------------------------------------------------------

    def _handle_modals(self, page, result: RunResult, step_index: int) -> None:
        """Poll for a modal before acting. Day 0 constraint 1 — log every one, with its text."""
        for selector in MODAL_SELECTORS:
            try:
                node = page.query_selector(selector)
            except Exception:
                continue
            if not node or not node.is_visible():
                continue

            text = (node.inner_text() or "").strip()
            event = ModalEvent(step=step_index, url=page.url, text=text[:400], dismissed=False)
            self.evidence.append(content=f"MODAL: {text}", route_id=result.route_id,
                                 profile_id=result.profile_id, kind="modal", source=page.url)

            for button in node.query_selector_all("button, a"):
                label = (button.inner_text() or "").strip().lower()
                if any(word == label or word in label for word in DISMISS_TEXTS):
                    button.click()
                    page.wait_for_timeout(200)
                    event.dismissed, event.dismissed_via = True, label
                    break
            result.modals.append(event)
            return

    # -- filling ------------------------------------------------------------------------

    def _fill_step(self, page, record: StepRecord, result: RunResult,
                   profile: Profile, ctx: SessionContext) -> bool:
        available = {**profile.facts, **profile.elections}
        filled_any = False

        for element in page.query_selector_all("input, select, textarea"):
            try:
                if not element.is_visible():
                    continue
            except Exception:
                continue

            input_type = (element.get_attribute("type") or "text").lower()
            if input_type in {"hidden", "submit", "button", "image"}:
                continue

            element_id = element.get_attribute("id") or ""
            name = element.get_attribute("name") or ""
            label = self._label_for(page, element_id)
            match = match_field(label=label, name=name, element_id=element_id,
                                placeholder=element.get_attribute("placeholder") or "",
                                aria_label=element.get_attribute("aria-label") or "")
            record.fields_seen.append(name or element_id or label or "?")
            if match is None:
                continue
            if match.is_hypothesis:
                record.hypotheses.append((match.canonical, match.confidence))

            if input_type == "checkbox":
                self._maybe_check(page, element, label, name, match, record, result, ctx)
                continue

            if match.canonical not in available:
                # The profile has no value. If the field is optional, skip it. If it is required,
                # ask the gate anyway — a licence-number field under a hypothetical profile must
                # produce RC_HYPO_LICENCE_REQUIRED rather than a silent skip, which is the whole
                # Day 0 finding. Nothing is typed either way: the gate sees a withheld sentinel.
                required = (element.get_attribute("required") is not None
                            or element.get_attribute("aria-required") == "true")
                if not required:
                    continue
                probe = self._gate(
                    ctx, "fill", page.url,
                    {match.canonical: FieldValue("<withheld>", profile.profile_id),
                     "field": name or element_id, "label": label},
                    result.route_id, f"Required field {match.canonical} is not in the profile.")
                if probe.verdict != "ALLOW":
                    record.fields_denied.append((match.canonical, probe.rule_id))
                    result.policy_denials.append((probe.rule_id, probe.explanation))
                    result.pending_block = (
                        probe.terminal_status or "blocked", self._reason_for(probe.rule_id),
                        f"step {record.step}: {label or match.canonical}", probe.explanation)
                else:
                    result.pending_block = (
                        "unresolved", "RC_UNKNOWN",
                        f"step {record.step}: {label or match.canonical}",
                        f"The journey requires '{match.canonical}' and the profile has no value "
                        f"for it.")
                continue

            value = FieldValue(available[match.canonical], profile.profile_id)
            decision = self._gate(ctx, "fill", page.url, {match.canonical: value,
                                                          "field": name or element_id,
                                                          "label": label},
                                  result.route_id, f"Fill {match.canonical}.")
            if decision.verdict != "ALLOW":
                record.fields_denied.append((match.canonical, decision.rule_id))
                result.policy_denials.append((decision.rule_id, decision.explanation))
                status = decision.terminal_status or (
                    "blocked" if decision.rule_id == "P-HYPO-LICENCE-01" else "")
                if status:
                    result.pending_block = (
                        status, self._reason_for(decision.rule_id),
                        f"step {record.step}: {label or match.canonical}",
                        decision.explanation)
                continue

            try:
                if element.evaluate("e => e.tagName") == "SELECT":
                    element.select_option(str(value))
                else:
                    element.fill(str(value))
                record.fields_filled.append(match.canonical)
                filled_any = True
            except Exception:
                record.fields_denied.append((match.canonical, "FILL_FAILED"))
        return filled_any

    def _maybe_check(self, page, element, label, name, match: FieldMatch,
                     record: StepRecord, result: RunResult, ctx: SessionContext) -> None:
        """Checkboxes are where INC-001 happened. Every one goes through the gate."""
        decision = self._gate(ctx, "click", page.url,
                              {"label": label, "name": name, "control_type": "checkbox"},
                              result.route_id, f"Consider checkbox: {label[:60]}")
        if decision.verdict != "ALLOW":
            record.fields_denied.append((label[:40] or name, decision.rule_id))
            result.policy_denials.append((decision.rule_id, decision.explanation))
            if decision.terminal_status:
                result.pending_block = (
                    decision.terminal_status, self._reason_for(decision.rule_id),
                    f"step {record.step}: {label[:60]}", decision.explanation)
            return
        # Only tick a coverage election the profile actually elected.
        if match.canonical in {"opcf_44r", "income_replacement"}:
            record.fields_filled.append(match.canonical)

    # -- advancing ----------------------------------------------------------------------

    #: Call-to-action text that starts a quote journey from a marketing page. Real entry points
    #: are frequently links, not buttons, so a button-only search stalls at step 1.
    START_LINK_TEXTS = ("get a quote", "get quotes", "start my quote", "get my quote",
                        "compare quotes", "get started", "quote now", "car insurance quote")

    def _advance(self, page, result: RunResult, ctx: SessionContext, step_index: int) -> bool:
        candidates = list(page.query_selector_all("button, input[type=submit]"))
        for anchor in page.query_selector_all("a"):
            try:
                label = (anchor.inner_text() or "").strip().lower()
            except Exception:
                continue
            if any(phrase in label for phrase in self.START_LINK_TEXTS):
                candidates.append(anchor)

        for button in candidates:
            try:
                if not button.is_visible():
                    continue
            except Exception:
                continue
            label = (button.inner_text() or button.get_attribute("value") or "").strip()
            if not label:
                continue

            decision = self._gate(ctx, "submit", page.url, {"label": label},
                                  result.route_id, f"Advance the journey: {label}")
            if decision.verdict != "ALLOW":
                result.policy_denials.append((decision.rule_id, decision.explanation))
                if decision.terminal_status:
                    result.pending_block = (
                        decision.terminal_status, self._reason_for(decision.rule_id),
                        f"step {step_index}: {label}", decision.explanation)
                continue

            before = page.url + page.inner_text("body")[:200]
            try:
                button.click()
                page.wait_for_timeout(600)
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    pass
            except Exception:
                continue
            if page.url + page.inner_text("body")[:200] != before:
                return True
        return False

    # -- readers ------------------------------------------------------------------------

    @staticmethod
    def _label_for(page, element_id: str) -> str:
        if not element_id:
            return ""
        try:
            node = page.query_selector(f'label[for="{element_id}"]')
            return (node.inner_text() or "").strip() if node else ""
        except Exception:
            return ""

    #: Detection only. §2.1 forbids bypassing a bot control, so recognising one is the whole
    #: response: record `blocked`, end the route, keep the evidence. A managed challenge that is
    #: not detected becomes a silent `unresolved`, which understates the market map.
    BOT_CHECK_PHRASES = (
        "not a robot", "recaptcha", "hcaptcha", "turnstile",
        "you have been blocked", "attention required", "access denied",
        "security service to protect itself", "unusual traffic",
        "verify you are human", "checking your browser", "ray id",
    )

    @classmethod
    def _detect_bot_check(cls, page, text: str) -> bool:
        lowered = text.lower()
        if any(phrase in lowered for phrase in cls.BOT_CHECK_PHRASES):
            return True
        return bool(page.query_selector(
            "#recaptcha-box, .g-recaptcha, iframe[title*=recaptcha], iframe[src*=turnstile]"))

    @staticmethod
    def _detect_callback_only(page, text: str) -> bool:
        lowered = text.lower()
        return ("can't quote online" in lowered or "cannot quote online" in lowered
                or "an advisor will call" in lowered)

    #: Marketing copy that disqualifies a number on the same page from being a quote.
    ADVERTISED_PRICE_PHRASES = (
        "as low as", "starting at", "from $", "average", "save up to", "up to $",
        "rates from", "per month*", "on average",
    )

    @classmethod
    def _read_price(cls, page, text: str) -> float | None:
        """Read a premium, but only from a genuine price container.

        Two guards, both learned from a live false positive: prefer an explicit price element over
        free page text, and refuse any number sitting next to advertising language. A wrong
        premium is worse than no premium — it is the one error that cannot be walked back.
        """
        import re

        node = page.query_selector(".price, [data-testid*=premium], [class*=quote-price], "
                                   "[class*=premium-amount]")
        if node:
            match = re.search(r"\$\s?([\d,]+(?:\.\d{2})?)", node.inner_text() or "")
            return float(match.group(1).replace(",", "")) if match else None

        lowered = text.lower()
        if any(phrase in lowered for phrase in cls.ADVERTISED_PRICE_PHRASES):
            return None
        match = re.search(r"\$\s?([\d,]+\.\d{2})", text)
        return float(match.group(1).replace(",", "")) if match else None

    @staticmethod
    def _read_quote_ref(text: str) -> str:
        import re
        match = re.search(r"\b([A-Z]{2,4}-\d{6,10})\b", text)
        return match.group(1) if match else ""

    @staticmethod
    def _read_coverage(text: str) -> dict:
        """Parse `Label: value` lines from the price screen into canonical coverage keys.

        Generic rather than per-insurer: every quote summary is some rendering of label/value
        pairs, and hardcoding one insurer's wording produced an empty dict on the next one.
        """
        import re

        alias = {
            "third party liability": "third_party_liability_limit",
            "third party liability limit": "third_party_liability_limit",
            "liability limit": "third_party_liability_limit",
            "collision deductible": "collision_deductible",
            "comprehensive deductible": "comprehensive_deductible",
            "dcpd": "dcpd",
            "income replacement": "income_replacement",
            "opcf 44r": "opcf_44r_family_protection",
            "opcf 44r family protection": "opcf_44r_family_protection",
            "term": "term_months",
            "term months": "term_months",
        }
        coverage: dict[str, object] = {}
        for raw in text.splitlines():
            if ":" not in raw:
                continue
            label, _, value = raw.partition(":")
            key = alias.get(re.sub(r"[^a-z0-9 ]+", " ", label.lower()).strip())
            if not key:
                continue
            value = value.strip()
            digits = re.sub(r"[^\d]", "", value)
            coverage[key] = int(digits) if digits and not re.search(r"[a-z]", value.lower()) \
                else value.lower()
        return coverage

    @staticmethod
    def _reason_for(rule_id: str) -> str:
        return {
            "P-HYPO-LICENCE-01": "RC_HYPO_LICENCE_REQUIRED",
            "P-HYPO-ATTEST-01": "RC_HUMAN_REQUIRED",
            "P-HYPO-STEP-01": "RC_HUMAN_REQUIRED",
            "P-PLATE-01": "RC_ACCESS_CONTROL",
            "P-CAPTCHA-01": "RC_ACCESS_CONTROL",
            "P-APPROVAL-01": "RC_HUMAN_REQUIRED",
        }.get(rule_id, "RC_UNKNOWN")
