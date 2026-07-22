# FAQ

**Does SynthAudit need the real dataset the synthetic one imitates?**
No. That is the point. Fidelity, utility, and privacy suites compare
synthetic to real; SynthAudit audits the released file alone, which is the
situation of everyone who downloads a benchmark.

**My dataset has physical conservation laws. Will it be punished?**
No. Relations among non-target columns are classified as structural
constraints, not leakage, and are only charged as redundancy for feature
views. Tennessee Eastman carries nineteen such constraints and grades B;
BATADAL's hydraulics grade A. The failing grades in our cohort all come
from targets that sit inside recovered relations.

**Isn't near-perfect accuracy sometimes legitimate?**
Sometimes, and the index treats it as a *headroom* problem, not a leakage
verdict. Only trivial-mechanism evidence (an equation, a rule, a threshold,
a dominant single feature, or near-determinism in skill terms) drives the
label-integrity pillar.

**Why did my highly imbalanced dataset score so well on L?**
Because raw accuracy is not evidence. All classification scores are skill
over the majority baseline. A 99.9 percent constant label predicted at 99.9
percent accuracy has zero skill.

**Can a generator evade the audit by adding noise to derived columns?**
Up to a price. The paper's leakage-sensitivity bound shows escaping the
label-integrity pillar requires noise of at least $(1-s_0)/s_0$ times the
target variance (one ninth at defaults), by which point the leak has lost
most of its value. Determined adversaries remain future work, and the
threat model is honest-but-sloppy generators.

**Does a grade A mean the dataset is realistic or private?**
No. The index scores internal benchmark validity only. It says nothing
about fidelity to any real population, privacy, or societal harms, and the
pillar vector should always accompany the scalar.

**Which data shapes are supported?**
Single-table tabular and telemetry-style data. Relational schemas, long
time series, images, and text need dedicated miners and are on the roadmap.

**Why did the causal scan return so few edges?**
It is advisory by design: derived columns are removed first (determinism
breaks the faithfulness assumption), variables are capped for tractability,
and sortability diagnostics warn when recovered structure may be a scale
artifact.

**How do I cite SynthAudit?**
See `CITATION.cff` in the repository root; a methodology paper is under
submission and the citation will be updated on acceptance.
