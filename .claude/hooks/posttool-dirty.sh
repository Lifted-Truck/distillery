#!/usr/bin/env bash
# PostToolUse(Edit|Write|MultiEdit): mark the tree dirty. Cleared by ./verify.
# Cheap on purpose — running the full oracle on every edit is the wrong tempo;
# the Stop gate is where dirtiness gets cashed out.
mkdir -p .harness
date -u +%FT%TZ > .harness/dirty
exit 0
