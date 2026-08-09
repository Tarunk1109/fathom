# FATHOM — developer entry points.
#
# Deliberately thin. Every target is a single stdlib Python command, so anything here can be run
# directly without make. No dependency is introduced by this file.

PYTHON ?= python3

.PHONY: help sweep test check hooks unhook

help:
	@echo "FATHOM"
	@echo "  make sweep    PII sweep across the repo, including out/ and docs/ (Prime Directives 2.1)"
	@echo "  make test     unit tests (stdlib unittest)"
	@echo "  make check    sweep + test — run before every commit"
	@echo "  make hooks    install the pre-commit hook that runs the sweep"
	@echo "  make unhook   uninstall it"

sweep:
	@$(PYTHON) tools/pii_sweep.py

test:
	@$(PYTHON) -m unittest discover -s tests -v

check: sweep test

hooks:
	@git config core.hooksPath .githooks
	@echo "pre-commit hook installed — the PII sweep now runs before every commit."

unhook:
	@git config --unset core.hooksPath || true
	@echo "pre-commit hook removed."
