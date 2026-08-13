/* FATHOM — instrument UI. Vanilla JS, no framework, no build step (final.md §A4). */
(function () {
  "use strict";

  const DATA = JSON.parse(document.getElementById("fathom-data").textContent);
  const STAGE_LABELS = ["surface", "entry", "intake", "vehicle", "driver", "coverage", "price"];
  const REDUCE_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ------------------------------------------------------------------------------------
  // Small helpers
  // ------------------------------------------------------------------------------------

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $all = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) for (const k in attrs) {
      if (k === "class") node.className = attrs[k];
      else if (k === "html") node.innerHTML = attrs[k];
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), attrs[k]);
      else node.setAttribute(k, attrs[k]);
    }
    (children || []).forEach((c) => { if (c != null) node.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return node;
  }

  // SVG elements MUST be created in the SVG namespace — document.createElement("line") etc.
  // silently produces an inert HTMLUnknownElement that never renders as a shape. Found live:
  // the chart was empty (295 non-rendering child nodes, all namespaceURI xhtml instead of svg)
  // before this fix. Every shape/line/text/group inside an <svg> goes through this, not el().
  const SVG_NS = "http://www.w3.org/2000/svg";
  function svgEl(tag, attrs, children) {
    const node = document.createElementNS(SVG_NS, tag);
    if (attrs) for (const k in attrs) {
      if (k === "class") node.setAttribute("class", attrs[k]);
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), attrs[k]);
      else node.setAttribute(k, attrs[k]);
    }
    (children || []).forEach((c) => { if (c != null) node.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return node;
  }

  function fmtMoney(n) {
    if (n == null) return "—";
    return "$" + n.toLocaleString("en-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function plainStatus(status) {
    const MAP = {
      quoted_comparable: "Returned a price", quoted_non_comparable: "Returned a non-comparable price",
      estimate_only: "Estimate only", callback_required: "Callback required",
      manual_handoff: "Stopped for a human checkpoint", ineligible: "Ineligible",
      affinity_restricted: "Affinity restricted", specialty_only: "Specialty only",
      duplicate_rate_source: "Duplicate rate source", not_currently_writing: "Not writing new business",
      blocked: "Blocked", unreachable: "Unreachable", unresolved: "Unresolved",
      computed: "Computed", reconnaissance_pending: "Not yet attempted",
    };
    return MAP[status] || status;
  }

  function plainReason(code) {
    const MAP = {
      RC_HYPO_LICENCE_REQUIRED: "Stopped at a licence requirement a hypothetical profile cannot supply",
      licence_number_required_hypothetical_profile: "Stopped at a licence requirement a hypothetical profile cannot supply",
      RC_ACCESS_CONTROL: "Stopped by an access control (CAPTCHA / bot check)",
      access_control_encountered: "Stopped by an access control (CAPTCHA / bot check)",
      RC_HUMAN_REQUIRED: "Requires a human checkpoint",
      human_checkpoint_required: "Requires a human checkpoint",
      RC_LICENCE_CLASS: "Licence class insufficient",
      RC_MEMBERSHIP: "Membership or group required",
    };
    return MAP[code] || (code ? code.replace(/_/g, " ").toLowerCase() : "");
  }

  function statusColorClass(status, reasonCode) {
    if (status === "quoted_comparable" || status === "quoted_non_comparable") return "reached";
    if (status === "unresolved" || status === "reconnaissance_pending") return "unknown";
    if (status === "blocked" && (reasonCode === "RC_ACCESS_CONTROL")) return "refused";
    if (status === "blocked") return "obstructed";
    if (status === "callback_required" || status === "manual_handoff") return "obstructed";
    if (status === "ineligible" || status === "affinity_restricted" || status === "specialty_only") return "refused";
    return "unknown";
  }

  // ------------------------------------------------------------------------------------
  // Canonical JSON — must byte-match Python's json.dumps(sort_keys=True,
  // separators=(",",":"), ensure_ascii=False), because the audit/evidence chain hashes
  // were computed with exactly that serialization (packages/policy/audit.py:canonical_json).
  // ------------------------------------------------------------------------------------

  function canonicalStringify(value) {
    if (value === null || typeof value !== "object") return JSON.stringify(value);
    if (Array.isArray(value)) return "[" + value.map(canonicalStringify).join(",") + "]";
    const keys = Object.keys(value).sort();
    return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonicalStringify(value[k])).join(",") + "}";
  }

  async function sha256Hex(text) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  // Must exactly match packages/policy/audit.py:AuditEntry.hashable() — same 14 fields minus
  // entry_hash, same values. All 14 are round-tripped into DATA.audit.entries by build_ui.py.
  function auditHashable(entry) {
    return {
      index: entry.index, timestamp: entry.timestamp, session_id: entry.session_id,
      route_id: entry.route_id, profile_id: entry.profile_id, action_kind: entry.action_kind,
      target_safe: entry.target_safe, payload_fields: entry.payload_fields,
      payload_digest: entry.payload_digest, rationale_redacted: entry.rationale_redacted,
      verdict: entry.verdict, rule_id: entry.rule_id, explanation: entry.explanation,
      prev_hash: entry.prev_hash,
    };
  }

  // ------------------------------------------------------------------------------------
  // Navigation
  // ------------------------------------------------------------------------------------

  function goto(view) {
    $all(".view").forEach((v) => { v.hidden = v.dataset.view !== view; });
    $all(".rail-item").forEach((b) => {
      const active = b.dataset.goto === view;
      b.setAttribute("aria-current", active ? "page" : "false");
    });
    document.documentElement.dataset.view = view;
    if (location.hash.slice(1) !== view) history.replaceState(null, "", "#" + view);
    if (view === "sounding" && !renderSounding.done) renderSounding();
  }

  $all(".rail-item").forEach((b) => b.addEventListener("click", () => goto(b.dataset.goto)));
  window.addEventListener("hashchange", () => {
    const v = location.hash.slice(1);
    if (v) goto(v);
  });

  // ------------------------------------------------------------------------------------
  // View: Sounding
  // ------------------------------------------------------------------------------------

  function renderSounding() {
    renderSoundingChart();
    renderSoundingProse();
    renderMetricRow();
    renderScorecard();
    renderSounding.done = true;
  }

  function renderSoundingChart() {
    const svg = $("#sounding-chart");
    const routes = DATA.depths.filter((d) => !d.is_synthetic).slice().sort((a, b) => b.stage_index - a.stage_index || a.registry_id.localeCompare(b.registry_id));

    const rowH = 26, stageW = 92, leftPad = 160, topPad = 30, bottomPad = 46;
    const width = leftPad + STAGE_LABELS.length * stageW + 40;
    const height = topPad + routes.length * rowH + bottomPad;
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("width", width);
    svg.setAttribute("height", height);
    svg.innerHTML = "";

    // Stage gridlines + labels
    STAGE_LABELS.forEach((label, i) => {
      const x = leftPad + i * stageW;
      const line = svgEl("line", { class: "sounding-gridline", x1: x, y1: topPad - 8, x2: x, y2: topPad + routes.length * rowH });
      svg.appendChild(line);
      const t = svgEl("text", { class: "sounding-stage-label", x: x, y: topPad - 14, "text-anchor": "middle" });
      t.textContent = label.toUpperCase();
      svg.appendChild(t);
    });
    const surfaceY = topPad;
    svg.appendChild(svgEl("line", { class: "sounding-surface", x1: leftPad - 140, y1: surfaceY, x2: width - 20, y2: surfaceY }));

    const tooltip = $("#sounding-tooltip") || (function () {
      const t = el("div", { class: "sounding-tooltip", id: "sounding-tooltip" });
      document.body.appendChild(t);
      return t;
    })();

    routes.forEach((route, i) => {
      const y = topPad + i * rowH + rowH / 2;
      const xEnd = leftPad + route.stage_index * stageW;
      const colorClass = statusColorClass(route.status, route.reason_code);

      const label = svgEl("text", { class: "sounding-route-label", x: leftPad - 10, y: y + 3, "text-anchor": "end" });
      label.textContent = route.brand.length > 22 ? route.brand.slice(0, 21) + "…" : route.brand;
      svg.appendChild(label);

      const line = svgEl("line", {
        class: "sounding-line " + colorClass, x1: leftPad, y1: surfaceY, x2: leftPad, y2: y,
      });
      svg.appendChild(line);

      const marker = svgEl("circle", { class: "sounding-marker " + colorClass, cx: leftPad, cy: surfaceY });
      svg.appendChild(marker);

      const hitArea = svgEl("rect", {
        x: leftPad - 4, y: y - rowH / 2, width: STAGE_LABELS.length * stageW, height: rowH,
        fill: "transparent", style: "cursor:pointer",
      });
      hitArea.addEventListener("mousemove", (e) => showTooltip(tooltip, e, route));
      hitArea.addEventListener("mouseleave", () => { tooltip.style.display = "none"; });
      hitArea.addEventListener("click", () => { goto("outcomes"); setTimeout(() => highlightOutcome(route.registry_id), 60); });
      svg.appendChild(hitArea);

      const animate = () => {
        line.setAttribute("x2", leftPad);
        marker.setAttribute("cx", leftPad); marker.setAttribute("cy", surfaceY);
        if (REDUCE_MOTION) {
          line.setAttribute("x2", xEnd);
          marker.setAttribute("cx", xEnd); marker.setAttribute("cy", y);
          return;
        }
        const start = performance.now() + i * 14;
        const dur = 420;
        function step(now) {
          const t = Math.max(0, Math.min(1, (now - start) / dur));
          const eased = 1 - Math.pow(1 - t, 3);
          const cx = leftPad + (xEnd - leftPad) * eased;
          line.setAttribute("x2", cx);
          marker.setAttribute("cx", cx);
          marker.setAttribute("cy", y);
          if (t < 1) requestAnimationFrame(step); else { line.setAttribute("x2", xEnd); marker.setAttribute("cx", xEnd); }
        }
        requestAnimationFrame(step);
      };
      animate();
    });
  }

  function showTooltip(tooltip, evt, route) {
    tooltip.style.display = "block";
    tooltip.style.left = (evt.clientX + 16) + "px";
    tooltip.style.top = (evt.clientY + 12) + "px";
    tooltip.innerHTML = "";
    tooltip.appendChild(el("div", { class: "tt-title" }, [route.brand]));
    tooltip.appendChild(el("div", {}, [plainStatus(route.status) + (route.reason_code ? " — " + plainReason(route.reason_code) : "")]));
    tooltip.appendChild(el("div", { class: "tt-meta" }, [route.registry_id + "  ·  stage: " + route.stage_label]));
    if (route.note) tooltip.appendChild(el("div", { class: "tt-meta" }, [route.note]));
  }

  function renderSoundingProse() {
    const market = DATA.depths.filter((d) => !d.is_synthetic);
    const blocked = market.filter((d) => d.status === "blocked");
    const accessControl = blocked.filter((d) => d.reason_code === "RC_ACCESS_CONTROL");
    const licence = market.filter((d) => (d.reason_code || "").indexOf("LICENCE") >= 0 || (d.reason_code || "").indexOf("licence") >= 0);
    const unresolved = market.filter((d) => d.status === "unresolved");
    const priced = market.filter((d) => d.stage_label === "price");
    const total = DATA.metrics.distinct_rate_sources_total || market.length;

    const sentence = `${total} distinct rate sources surveyed. ${priced.length} reached a returned price. ` +
      `${accessControl.length} blocked by access control, ${licence.length} stopped at a licence requirement, ` +
      `${unresolved.length} unresolved.`;
    $("#sounding-prose").textContent = sentence;
  }

  function renderMetricRow() {
    const row = $("#metric-row");
    row.innerHTML = "";
    const METRICS = [
      ["market_completion", "Market completion"],
      ["comparable_quote_yield", "Comparable quote yield"],
      ["evidence_rate", "Evidence rate"],
      ["duplicate_suppression", "Duplicate suppression"],
      ["freshness", "Freshness"],
    ];
    METRICS.forEach(([key, label]) => {
      const value = DATA.metrics[key] || "—";
      const tile = el("div", { class: "metric-tile" }, [
        el("div", { class: "metric-tile-label" }, [label]),
        el("div", { class: "metric-tile-value mono" }, [value]),
      ]);
      row.appendChild(tile);
    });
    const unresolvedCount = DATA.metrics.records_attempted != null
      ? (DATA.records.filter((r) => r.status === "unresolved").length) : 0;
    const tile = el("div", { class: "metric-tile" }, [
      el("div", { class: "metric-tile-label" }, ["Unresolved (kept in every denominator)"]),
      el("div", { class: "metric-tile-value mono unknown-metric" }, [String(unresolvedCount)]),
    ]);
    row.appendChild(tile);
  }

  function renderScorecard() {
    const grid = $("#scorecard-grid");
    grid.innerHTML = "";
    const s = DATA.scorecard;
    const ITEMS = [
      ["Fabrications caught pre-report", s.fabrications_caught_pre_report, true],
      ["Fabrications shipped", s.fabrications_shipped, false],
      ["Policy rules, total", s.policy_rules_total, false],
      ["Policy rules LIVE in operation", s.policy_rules_live, false],
      ["Policy rules PARTIAL", s.policy_rules_partial, false],
      ["Concurrency bug found + fixed", s.concurrency_bug_found_and_fixed ? "yes" : "no", true],
      ["Sandbox routes run", s.sandbox_routes_run, false],
      ["Sandbox routes reaching a price", s.sandbox_routes_priced, false],
      ["Extraction accuracy, verified sample", s.extraction_accuracy_verified_sample, false],
    ];
    ITEMS.forEach(([label, value, flag]) => {
      grid.appendChild(el("div", { class: "scorecard-item" + (flag ? " flag" : "") }, [
        el("div", { class: "scorecard-item-label" }, [label]),
        el("div", { class: "scorecard-item-value mono" }, [String(value)]),
      ]));
    });
  }

  // ------------------------------------------------------------------------------------
  // View: Outcomes
  // ------------------------------------------------------------------------------------

  let outcomesSort = "depth";
  function renderOutcomes() {
    const computed = DATA.results.filter((r) => r.status === "computed");
    const rest = DATA.results.filter((r) => r.status !== "computed");

    const sorters = {
      depth: (a, b) => depthOf(b) - depthOf(a),
      price: (a, b) => (b.price.annual_premium || -1) - (a.price.annual_premium || -1),
      status: (a, b) => a.status.localeCompare(b.status),
    };
    const sorted = rest.slice().sort(sorters[outcomesSort]);

    $("#price-sort-note").hidden = outcomesSort !== "price";

    $("#outcomes-computed").innerHTML = "";
    if (computed.length) {
      $("#outcomes-computed").appendChild(el("div", { class: "outcomes-band-title" }, ["Computed (not retrieved)"]));
      computed.forEach((r) => $("#outcomes-computed").appendChild(outcomeRow(r)));
    }

    const container = $("#outcomes-estimated");
    container.innerHTML = "";
    container.appendChild(el("div", { class: "outcomes-band-title" }, ["Retrieved outcomes"]));
    sorted.forEach((r) => container.appendChild(outcomeRow(r)));
  }

  function depthOf(result) {
    const d = DATA.depths.find((x) => x.registry_id === result.registry_id);
    return d ? d.stage_index : 0;
  }

  function outcomeRow(r) {
    const record = DATA.records.find((x) => x.registry_id === r.registry_id) || {};
    const wrap = el("div", { class: "outcome-row", id: "outcome-" + r.registry_id });
    const colorClass = statusColorClass(r.status, r.reason_code);

    const summary = el("div", { class: "outcome-summary" }, [
      el("div", {}, [
        el("div", { class: "oc-brand" }, [record.brand_or_program || r.route_id, r.sandbox ? el("span", { class: "badge badge-sandbox", html: "&nbsp;SANDBOX" }) : null]),
        el("div", { class: "oc-underwriter" }, [record.legal_underwriter || ""]),
      ]),
      el("div", {}, [
        el("div", { class: "oc-cell-label" }, ["Status"]),
        el("div", { class: "status-word" }, [plainStatus(r.status)]),
      ]),
      el("div", {}, [
        el("div", { class: "oc-cell-label" }, ["Reason"]),
        el("div", { class: "reason-plain" }, [plainReason(r.reason_code)]),
        r.reason_code ? el("div", { class: "reason-code mono" }, [r.reason_code]) : null,
      ]),
      el("div", {}, [
        el("div", { class: "oc-cell-label" }, ["Verdict"]),
        el("span", { class: "verdict-pill verdict-" + r.assessment.verdict }, [r.assessment.verdict]),
      ]),
      el("div", {}, [
        el("div", { class: "oc-cell-label" }, ["Confidence"]),
        el("div", {}, [r.assessment.confidence_indicator]),
      ]),
      el("div", {}, [
        el("div", { class: "oc-cell-label" }, ["Annual"]),
        el("div", { class: "mono" }, [fmtMoney(r.price.annual_premium)]),
      ]),
      el("div", {}, [
        el("div", { class: "oc-cell-label" }, ["Evidence"]),
        el("div", { class: "mono" }, [(r.evidence.artifact_cids || []).length + " CIDs"]),
      ]),
    ]);
    summary.addEventListener("click", () => detail.classList.toggle("open"));

    const detail = el("div", { class: "outcome-detail" });
    if (r.variance_from_benchmark && r.variance_from_benchmark.length) {
      detail.appendChild(el("p", {}, ["Coverage variance from the §8.5 benchmark:"]));
      const ul = el("ul", { class: "variance-list" });
      r.variance_from_benchmark.forEach((v) => ul.appendChild(el("li", {}, [v])));
      detail.appendChild(ul);
    } else if (r.price.annual_premium != null) {
      detail.appendChild(el("div", { class: "variance-list match" }, ["Matches the benchmark package exactly."]));
    }
    if (r.price.annual_premium != null) {
      detail.appendChild(el("div", { class: "price-line mono" }, [fmtMoney(r.price.annual_premium) + " / year"]));
    }
    if (r.coverage && Object.keys(r.coverage).length) {
      const grid = el("div", { class: "ab-grid" });
      Object.entries(r.coverage).forEach(([k, v]) => {
        const state = String(v).toLowerCase();
        const stateClass = ["included", "excluded", "unavailable", "unknown"].includes(state) ? state : "unknown";
        grid.appendChild(el("div", { class: "ab-item" }, [
          el("div", {}, [k.replace(/_/g, " ")]),
          el("div", { class: "ab-state ab-state-" + stateClass }, [String(v)]),
        ]));
      });
      detail.appendChild(grid);
    }
    if (r.decline && r.decline.stopping_step) {
      detail.appendChild(el("p", {}, ["Stopped: " + el("span", {}, []).textContent + r.decline.stopping_step]));
      detail.appendChild(el("p", { class: "mono", style: "font-size:11px;color:var(--sounding)" }, [
        "Policy rules fired: " + (r.decline.policy_rules_fired || []).join(", ") || "none",
      ]));
    }
    if ((r.evidence.artifact_cids || []).length) {
      detail.appendChild(el("button", { class: "evidence-link", onclick: () => { goto("evidence"); setTimeout(() => filterEvidence(r.evidence.artifact_cids[0]), 60); } },
        ["View evidence → " + r.evidence.artifact_cids[0].slice(0, 24) + "…"]));
    }

    wrap.appendChild(summary);
    wrap.appendChild(detail);
    return wrap;
  }

  function highlightOutcome(registryId) {
    const node = document.getElementById("outcome-" + registryId);
    if (!node) return;
    node.scrollIntoView({ behavior: REDUCE_MOTION ? "auto" : "smooth", block: "center" });
    node.style.outline = "2px solid var(--reached)";
    setTimeout(() => { node.style.outline = ""; }, 1500);
    const detail = $(".outcome-detail", node);
    if (detail) detail.classList.add("open");
  }

  $("#outcomes-sort").addEventListener("change", (e) => { outcomesSort = e.target.value; renderOutcomes(); });

  // ------------------------------------------------------------------------------------
  // View: Market
  // ------------------------------------------------------------------------------------

  let marketLayer = "brand";
  function renderMarket() {
    const svg = $("#market-graph");
    svg.innerHTML = "";
    const nodes = DATA.graph_nodes;

    const rowH = 30, leftColX = 260, rightColX = 620, topPad = 20;
    const height = topPad * 2 + Math.max(nodes.length, nodes.reduce((a, n) => a + n.brands.length, 0)) * rowH;
    const width = 880;
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("width", width);
    svg.setAttribute("height", height);

    // The right-column grouping key. For the brand/distributor layer this must be the actual
    // dedup unit (rate_source_id), never the raw legal_underwriter text — multiple *unrelated*
    // rate sources legitimately share the literal placeholder "unknown — not yet verified" or
    // "unknown — requires regulator evidence", and keying on that string collapsed them onto one
    // row, sending edges to the wrong target and producing a tangle of crossing lines. Found by
    // actually looking at the rendered graph, not by reading the code.
    //
    // For the underwriter/group layer, collapsing rows that share a real name IS the point of
    // that lens — but an "unknown" placeholder still needs per-node disambiguation so unrelated
    // unknowns don't merge there either.
    function rightKeyFor(node) {
      if (marketLayer === "brand" || marketLayer === "distributor") return node.rate_source_id;
      const text = marketLayer === "group" ? node.insurer_group : node.legal_underwriter;
      return (text || "").toLowerCase().startsWith("unknown") ? text + "::" + node.rate_source_id : text;
    }
    function rightLabelFor(node) {
      return marketLayer === "group" ? node.insurer_group : node.legal_underwriter;
    }

    let leftY = topPad, rightY = topPad;
    const rightYByKey = {};
    const rightLabelByKey = {};

    nodes.forEach((node) => {
      const key = rightKeyFor(node);
      if (!(key in rightYByKey)) {
        rightYByKey[key] = rightY; rightY += rowH;
        rightLabelByKey[key] = rightLabelFor(node);
      }
    });

    // Recompute canvas height to fit both columns properly.
    const totalLeftRows = nodes.reduce((a, n) => a + n.brands.length, 0);
    const finalHeight = topPad * 2 + Math.max(totalLeftRows, Object.keys(rightYByKey).length) * rowH;
    svg.setAttribute("viewBox", `0 0 ${width} ${finalHeight}`);
    svg.setAttribute("height", finalHeight);

    leftY = topPad;
    const edgesGroup = svgEl("g", {});
    const nodesGroup = svgEl("g", {});
    svg.appendChild(edgesGroup);
    svg.appendChild(nodesGroup);

    nodes.forEach((node) => {
      const ry = rightYByKey[rightKeyFor(node)];
      const groupKey = rightLabelFor(node);

      const brandsToShow = marketLayer === "brand" || marketLayer === "distributor" ? node.brands : [{ brand: groupKey, hypothesis_with: "", distribution_type: "" }];
      const shown = marketLayer === "brand" ? node.brands : [node]; // for underwriter/group layer, collapse to one row per underwriter

      if (marketLayer === "brand" || marketLayer === "distributor") {
        node.brands.forEach((b) => {
          const ly = leftY; leftY += rowH;
          const label = marketLayer === "distributor" ? (b.distribution_type || "unknown") + " — " + b.brand : b.brand;
          // A same-row edge is nearly horizontal and passes directly through this row's own
          // label — SVG <text> has no implicit background, so the stroke shows through the gaps
          // between glyphs and reads as a strikethrough. Found live: every left-column label
          // looked crossed out. An opaque backing rect (panel colour, sized to the label) fixes
          // it without restructuring the layout — edges duck visually behind the label.
          const shownLabel = label.length > 30 ? label.slice(0, 29) + "…" : label;
          const leftNode = svgEl("g", { class: "mg-node", transform: `translate(20,${ly})` });
          leftNode.appendChild(svgEl("circle", { r: 4 }));
          leftNode.appendChild(svgEl("rect", {
            x: 6, y: -7, width: 4 + shownLabel.length * 5.6, height: 14, fill: "var(--deep)",
          }));
          const t = svgEl("text", { x: 10, y: 4 }, [shownLabel]);
          leftNode.appendChild(t);
          leftNode.addEventListener("click", () => showEdgeDetail(node, b));
          nodesGroup.appendChild(leftNode);

          const dashed = !node.evidenced && !!b.hypothesis_with;
          const path = svgEl("path", {
            class: "mg-edge" + (dashed ? " dashed" : "") + (node.evidenced && node.brands.length > 1 ? " highlight" : ""),
            d: bezier(20 + 4, ly, leftColX, ry),
          });
          path.addEventListener("click", () => showEdgeDetail(node, b));
          edgesGroup.appendChild(path);
        });
      }
    });

    // Right column: underwriters / groups. Find the node(s) sharing this exact right-key
    // (there may be several when the layer legitimately collapses multiple rate sources under
    // one real underwriter/group name) rather than a naive text match against the raw label,
    // which would mis-resolve disambiguated "unknown" keys back to the wrong node.
    Object.entries(rightYByKey).forEach(([key, ry]) => {
      const matchingNodes = nodes.filter((n) => rightKeyFor(n) === key);
      const matchingNode = matchingNodes[0];
      const rawLabel = rightLabelByKey[key] || "unknown";
      const rightLabel = rawLabel.length > 34 ? rawLabel.slice(0, 33) + "…" : rawLabel;
      const totalBrands = matchingNodes.reduce((a, n) => a + n.brands.length, 0);
      const anyEvidenced = matchingNodes.some((n) => n.evidenced);
      const maxSignals = Math.max(...matchingNodes.map((n) => n.signals_agreeing));
      const g = svgEl("g", { class: "mg-node underwriter", transform: `translate(${leftColX},${ry})` });
      g.appendChild(svgEl("circle", { r: 5 }));
      g.appendChild(svgEl("rect", { x: 7, y: -7, width: 5 + rightLabel.length * 5.6, height: 26, fill: "var(--deep)" }));
      g.appendChild(svgEl("text", { x: 12, y: 4 }, [rightLabel]));
      g.appendChild(svgEl("text", { class: "mg-sub", x: 12, y: 16 }, [maxSignals + " signals"]));
      if (totalBrands > 1 && anyEvidenced) g.classList.add("highlight");
      g.addEventListener("click", () => matchingNode && showEdgeDetail(matchingNode, null));
      nodesGroup.appendChild(g);
    });

    renderResidualManualPanel();
  }

  // final.md B2, revisited/scoped to extraction-only. Rows are parsed straight out of the real
  // public Facility Association manual — never a quote, estimate, or premium. See
  // docs/RESIDUAL_MARKET.md for what was extracted and what was deliberately left out.
  function renderResidualManualPanel() {
    const rm = DATA.residual_manual;
    const panel = $("#residual-manual-panel");
    if (!rm || !rm.available) { panel.hidden = true; return; }
    panel.hidden = false;
    $("#residual-manual-disclaimer").textContent = rm.disclaimer;

    const body = $("#residual-manual-body");
    body.innerHTML = "";
    body.appendChild(el("p", { class: "mono" }, [
      `${rm.table_name} — pages ${rm.page_range[0]}–${rm.page_range[1]} — ${rm.row_count} rows extracted — `,
      el("a", { href: rm.source.url, target: "_blank", rel: "noopener" }, ["source PDF"]),
      ` (retrieved ${rm.source.retrieved_at.slice(0, 10)}, sha256 ${rm.source.file_sha256.slice(0, 12)}…)`,
    ]));

    const table = el("table", { class: "residual-table" });
    const thead = el("thead", {}, [el("tr", {}, [
      el("th", {}, ["Location"]), el("th", {}, ["County / District / Municipality"]),
      el("th", {}, ["Territory"]), el("th", {}, ["Stat code"]), el("th", {}, ["Source page"]),
    ])]);
    const tbody = el("tbody", {}, rm.sample_rows.map((r) => el("tr", {}, [
      el("td", {}, [r.location]), el("td", {}, [r.county_district_municipality]),
      el("td", {}, [r.territory]), el("td", {}, [r.stat_code]),
      el("td", { class: "mono" }, [String(r.source_page)]),
    ])));
    table.appendChild(thead); table.appendChild(tbody);
    body.appendChild(table);
    body.appendChild(el("p", { class: "view-sub" }, [rm.sample_note]));

    const notList = el("ul", { class: "not-extracted-list" }, rm.not_extracted.map((n) => el("li", {}, [
      el("strong", {}, [n.category]), ` (${n.location_in_manual}) — not extracted: ${n.reason}`,
    ])));
    body.appendChild(el("p", {}, ["Deliberately not extracted:"]));
    body.appendChild(notList);
  }

  function bezier(x1, y1, x2, y2) {
    const mx = (x1 + x2) / 2;
    return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
  }

  function showEdgeDetail(node, brand) {
    const panel = $("#market-edge-detail");
    panel.hidden = false;
    $("#market-edge-title").textContent = node.legal_underwriter + (node.brands.length > 1 ? ` — ${node.brands.length} brands collapse here` : "");
    const body = $("#market-edge-body");
    body.innerHTML = "";
    body.appendChild(el("p", {}, [
      "Signals agreeing: " + el("span", { class: "mono" }, []).textContent + node.signals_agreeing +
      (node.evidenced ? " — evidenced merge (≥20.3's two-signal rule)" : " — single signal, hypothesis only, not merged"),
    ]));
    const list = el("ul", {});
    node.brands.forEach((b) => {
      list.appendChild(el("li", {}, [
        b.brand + " (" + (b.distribution_type || "unknown") + ")",
        b.hypothesis_with ? el("span", { class: "mono", style: "color:var(--obstructed)" }, [" — hypothesis with " + b.hypothesis_with]) : null,
      ]));
    });
    body.appendChild(list);
    if (node.rate_source_id === "rs_0010") {
      body.appendChild(el("p", { style: "color:var(--reached)" }, [
        "Pilot, Elite and Traders General amalgamated into Aviva Insurance Company of Canada, effective 2026-01-01. Source: avivacanada.com.",
      ]));
    }
  }

  $all("#layer-toggle button").forEach((b) => b.addEventListener("click", () => {
    marketLayer = b.dataset.layer;
    $all("#layer-toggle button").forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
    renderMarket();
  }));

  // ------------------------------------------------------------------------------------
  // View: Frontier
  // ------------------------------------------------------------------------------------

  function renderFrontier() {
    const ladder = $("#frontier-ladder");
    ladder.innerHTML = "";
    if (!DATA.frontier.ladder.length) {
      ladder.appendChild(el("p", { style: "color:var(--sounding)" }, [
        "No unlockable rung is evidenced yet. Most attempted routes stopped at this build's own " +
        "capability limit rather than a market-eligibility refusal — see docs/LIMITATIONS.md.",
      ]));
    }
    DATA.frontier.ladder.forEach((rung) => {
      const body = el("div", { class: "frontier-rung-body" });
      rung.records.forEach((r) => body.appendChild(el("div", { class: "frontier-record-row" }, [
        el("span", { class: "mono" }, [r.registry_id]), el("span", {}, [r.brand]),
        el("span", { class: "mono", style: "color:var(--sounding)" }, [r.reason_code || ""]),
      ])));
      const rung_el = el("div", { class: "frontier-rung" }, [
        el("div", { class: "frontier-rung-head", onclick: () => body.classList.toggle("open") }, [
          el("div", { class: "frontier-rung-count" }, [String(rung.opens_rate_sources)]),
          el("div", {}, [
            el("div", { class: "frontier-rung-label" }, [rung.label]),
            el("div", { class: "mono", style: "font-size:11px;color:var(--sounding)" }, ["opens " + rung.opens_rate_sources + " distinct rate source(s)"]),
          ]),
        ]),
        body,
      ]);
      ladder.appendChild(rung_el);
    });

    const closed = $("#frontier-closed");
    closed.innerHTML = "";
    DATA.frontier.closed_regardless.forEach((r) => closed.appendChild(el("div", { class: "frontier-record-row" }, [
      el("span", { class: "mono" }, [r.registry_id]), el("span", {}, [r.brand]),
      el("span", { class: "mono", style: "color:var(--sounding)" }, [r.reason_code || "unresolved (capability limit)"]),
    ])));
  }

  // ------------------------------------------------------------------------------------
  // View: Gate
  // ------------------------------------------------------------------------------------

  function renderGate() {
    const filterSelect = $("#gate-rule-filter");
    if (!filterSelect.dataset.built) {
      const ruleIds = Array.from(new Set(DATA.audit.entries.map((e) => e.rule_id))).sort();
      ruleIds.forEach((rid) => filterSelect.appendChild(el("option", { value: rid }, [rid])));
      filterSelect.dataset.built = "1";
      filterSelect.addEventListener("change", renderGateLog);
    }
    renderGateLog();
    renderEnforcementTable();
  }

  function renderGateLog() {
    const filter = $("#gate-rule-filter").value;
    const entries = DATA.audit.entries.filter((e) => !filter || e.rule_id === filter);
    const table = $("#gate-log");
    table.innerHTML = "";
    table.appendChild(el("tr", {}, [
      el("th", {}, ["#"]), el("th", {}, ["Verdict"]), el("th", {}, ["Rule"]),
      el("th", {}, ["Action"]), el("th", {}, ["Route"]), el("th", {}, ["Target"]), el("th", {}, ["Timestamp"]),
    ]));
    entries.slice(-400).reverse().forEach((e) => {
      table.appendChild(el("tr", {}, [
        el("td", { class: "idx mono" }, [String(e.index)]),
        el("td", {}, [el("span", { class: "verdict-tag " + e.verdict }, [e.verdict])]),
        el("td", { class: "rule mono" }, [e.rule_id]),
        el("td", {}, [e.action_kind]),
        el("td", { class: "mono" }, [e.route_id]),
        el("td", { class: "mono", style: "color:var(--sounding);font-size:11px" }, [e.target_safe]),
        el("td", { class: "mono", style: "font-size:11px;color:var(--sounding)" }, [e.timestamp]),
      ]));
    });
  }

  function renderEnforcementTable() {
    const table = $("#enforcement-table");
    table.innerHTML = "";
    table.appendChild(el("tr", {}, [el("th", {}, ["Directive area"]), el("th", {}, ["Mechanism"]), el("th", {}, ["Status"])]));
    DATA.enforcement.forEach((row) => {
      table.appendChild(el("tr", {}, [
        el("td", {}, [row.area]),
        el("td", { class: "mono", style: "font-size:11px" }, [row.mechanism]),
        el("td", {}, [el("span", { class: "status-tag " + row.status }, [row.status])]),
      ]));
    });
  }

  $("#verify-chain-btn").addEventListener("click", async () => {
    const resultEl = $("#verify-chain-result");
    resultEl.textContent = "verifying…";
    resultEl.className = "verify-result";
    const entries = DATA.audit.entries;
    let prevHash = "0".repeat(64);
    for (let i = 0; i < entries.length; i++) {
      const e = entries[i];
      if (e.index !== i) {
        resultEl.textContent = `BROKEN at index ${i}: stored index is ${e.index}, expected ${i}`;
        resultEl.className = "verify-result broken";
        return;
      }
      if (e.prev_hash !== prevHash) {
        resultEl.textContent = `BROKEN at index ${i}: prev_hash does not match the preceding entry`;
        resultEl.className = "verify-result broken";
        return;
      }
      const computed = await sha256Hex(canonicalStringify(auditHashable(e)));
      if (computed !== e.entry_hash) {
        resultEl.textContent = `BROKEN at index ${i}: entry_hash does not match the entry's contents (recomputed in-browser)`;
        resultEl.className = "verify-result broken";
        return;
      }
      prevHash = e.entry_hash;
      if (i % 40 === 0) resultEl.textContent = `verifying… ${i}/${entries.length}`;
    }
    resultEl.textContent = `chain intact — ${entries.length} entries verified in-browser`;
    resultEl.className = "verify-result ok";
  });

  // ------------------------------------------------------------------------------------
  // View: Evidence
  // ------------------------------------------------------------------------------------

  function renderEvidence() {
    const chainEl = $("#evidence-chain-status");
    chainEl.textContent = DATA.evidence.message;
    chainEl.className = "verify-result " + (DATA.evidence.chain_ok ? "ok" : "broken");
    filterEvidence("");
  }

  function filterEvidence(query) {
    const search = $("#evidence-search");
    if (query) search.value = query;
    const q = (search.value || "").toLowerCase();
    const list = $("#evidence-list");
    list.innerHTML = "";
    const filtered = DATA.evidence.artifacts.filter((a) =>
      !q || a.cid.toLowerCase().includes(q) || a.route_id.toLowerCase().includes(q) || a.source.toLowerCase().includes(q));
    filtered.slice().reverse().slice(0, 300).forEach((a) => {
      const row = el("div", { class: "evidence-row", onclick: () => openArtifact(a) }, [
        el("div", {}, [
          el("div", { class: "ev-cid" }, [a.cid]),
          el("div", { class: "ev-meta" }, [a.source]),
        ]),
        el("div", { class: "ev-meta mono" }, [a.route_id]),
        el("div", { class: "ev-meta mono" }, [a.kind]),
        el("div", { class: "ev-meta mono" }, [a.timestamp]),
      ]);
      list.appendChild(row);
    });
  }
  $("#evidence-search").addEventListener("input", () => filterEvidence());

  function openArtifact(a) {
    const modal = $("#artifact-modal");
    const body = $("#artifact-modal-body");
    body.innerHTML = "";
    body.appendChild(el("h2", { style: "font-family:var(--font-display);font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--sounding)" }, ["Evidence artifact"]));
    body.appendChild(el("p", { class: "mono", style: "font-size:11px;color:var(--reached)" }, [a.cid]));
    body.appendChild(el("p", { style: "font-size:12px;color:var(--sounding)" }, [
      a.route_id + "  ·  " + a.kind + "  ·  " + a.timestamp + "  ·  chain idx " + a.index,
    ]));
    if (a.redaction_rules_fired && a.redaction_rules_fired.length) {
      body.appendChild(el("p", { style: "font-size:11px;color:var(--obstructed)" }, ["Redacted: " + a.redaction_rules_fired.join(", ")]));
    }
    body.appendChild(el("pre", {}, [a.text_excerpt || "(no text captured)"]));
    modal.hidden = false;
  }
  $("#artifact-modal-close").addEventListener("click", () => { $("#artifact-modal").hidden = true; });
  $("#artifact-modal").addEventListener("click", (e) => { if (e.target.id === "artifact-modal") $("#artifact-modal").hidden = true; });

  // ------------------------------------------------------------------------------------
  // Boot
  // ------------------------------------------------------------------------------------

  $("#rail-generated").textContent = "generated " + (DATA.generated_at || "").slice(0, 19).replace("T", " ");

  renderOutcomes();
  renderMarket();
  renderFrontier();
  renderGate();
  renderEvidence();

  const initial = location.hash.slice(1) || "sounding";
  goto(initial);
})();
