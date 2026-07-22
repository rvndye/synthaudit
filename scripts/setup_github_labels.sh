#!/usr/bin/env bash
# Create the project's label set. Requires: gh auth login, run once after
# repository creation. Safe to re-run (failures on existing labels ignored).
set -uo pipefail
REPO="${1:-rvndye/synthaudit}"

label() { gh label create "$1" --repo "$REPO" --color "$2" --description "$3" 2>/dev/null || \
          gh label edit  "$1" --repo "$REPO" --color "$2" --description "$3"; }

label "type: bug"           d73a4a "Something is broken"
label "type: enhancement"   a2eeef "New capability or improvement"
label "type: docs"          0075ca "Documentation"
label "type: question"      d876e3 "Further information requested"
label "audit finding"       e67e22 "Generator artifact found in a public dataset"
label "module: identity"    0072B2 "Identity mining (M2)"
label "module: determinism" 0072B2 "Determinism sweep (M3)"
label "module: causal"      0072B2 "Causal scan (M4)"
label "module: leakage"     0072B2 "Leakage audit (M5)"
label "module: scoring"     009E73 "BTI and taxonomy"
label "module: reports"     009E73 "HTML/PDF/JSON exports"
label "module: cli"         009E73 "Command-line interface"
label "false positive"      c0392b "Screen fired on legitimate structure"
label "false negative"      8e44ad "Artifact the auditor missed"
label "good first issue"    7057ff "Good for newcomers"
label "help wanted"         008672 "Extra attention appreciated"
echo "labels configured for $REPO"
