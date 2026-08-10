# FATHOM — developer entry points.
#
# Deliberately thin. Every target is a single stdlib Python command, so anything here can be run
# directly without make. No dependency is introduced by this file.

PYTHON ?= python3

.PHONY: help sweep test check demo verify rules hooks unhook

help:
	@echo "FATHOM"
	@echo "  make sweep    PII sweep across the repo, including out/ and docs/ (Prime Directives 2.1)"
	@echo "  make test     unit tests (stdlib unittest)"
	@echo "  make check    sweep + test — run before every commit"
	@echo "  make demo     the gate, demonstrated: a denied bind + chain verification (16 step 6)"
	@echo "  make verify   verify the policy audit chain (judge-facing)"
	@echo "  make rules    list every policy rule and what it denies"
	@echo "  make hooks    install the pre-commit hook that runs the sweep"
	@echo "  make unhook   uninstall it"

sweep:
	@$(PYTHON) tools/pii_sweep.py

test:
	@$(PYTHON) -m unittest discover -s tests -v

check: sweep test

demo:
	@$(PYTHON) scripts/demo_gate.py --tamper

verify:
	@$(PYTHON) scripts/verify_chain.py --show 20

rules:
	@$(PYTHON) -c "import sys; sys.path.insert(0,'.'); \
	from packages.policy import DEFAULT_RULES; \
	[print(f'{r.rule_id:<20} {r.verdict:<9} {r.summary}') for r in DEFAULT_RULES]"

hooks:
	@git config core.hooksPath .githooks
	@echo "pre-commit hook installed — the PII sweep now runs before every commit."

unhook:
	@git config --unset core.hooksPath || true
	@echo "pre-commit hook removed."
