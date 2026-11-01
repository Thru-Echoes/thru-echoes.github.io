### One PR, held to a clean standard

*proofpress, October 2026*

> **evt\_002, Decision: agent proposal, revised by human**
>
> **Agent proposed:** ProofPress context-lineage fix design: one PR off origin/main \(fix/context-lineage\). Add a lineage resolver \(revision\_of, reproposal\_of, supersession edges; rank usable \> pending \> sent back; latest wins\) used by context\_v2, traverse\_graph\_v2 \(disclose\_v1 inherits\), and receipt\_v2. \[...\]

> **evt\_002, Human revised**
>
> Human kept the context-lineage design but rejected splitting the follow-ups: one PR must also fix the shadowed admission in review\_v2 and the uneven disclosure filtering in receipt\_v2 / traverse\_graph\_v2, then go through inline adversarial passes and gpt-6.1-sol passes before it is called good to go.

> **evt\_003, Contribution: human idea, AI built**
>
> Implementation plan for the ProofPress context-lineage PR \(fix/context-lineage off origin/main 4bd2047\): 5 TDD tasks \(resolver \+ context\_v2; \[...\]

> **evt\_004, Contribution: human idea, AI built**
>
> Reference patch for the context-lineage fix, built and verified on a throwaway detached copy of origin/main 4bd2047 \(kernel resolver, \[...\]

> **evt\_005, Decision: human proposal, accepted by human**
>
> Single ProofPress PR \(fix/context-lineage\): the context-lineage plan plus \(a\) review decisions that would be silently shadowed are refused, and \(b\) \[...\]

> **evt\_006, Contribution: human idea, AI built**
>
> ProofPress branch fix/context-lineage \(9 commits on origin/main 4bd2047, not pushed\): lineage-following blocked entries, fork guard, \[...\]

> **evt\_008, Correction**
>
> **Correction:** AI reported pyright as acceptable because the error count on touched files matched main \(33 errors in operations.py, events.py, control\_plane.py, test\_event\_store.py; 31 in basic mode\). The operator standard is pyright-clean on every modified file, so matching a dirty baseline is not a pass. Human flagged it; the errors are being fixed in the same PR before the confirmation review.

Links stored in these records: evt\_003 builds on evt\_002; evt\_004 builds on evt\_002; evt\_005 revises evt\_002; evt\_006 builds on evt\_005; evt\_008 corrects evt\_006.

### Too early to standardize verification

*TRACE, April 2026*

> **evt\_012, Decision: agent proposal, rejected by human**
>
> **Agent proposed:** Add structured verification event type to TRACE \(trace\_log\_verification with method, sample\_size, metric, result, ground\_truth\_source fields\) to directly map to rubric dimension E
>
> **Rationale:** Initial analysis identified that TRACE captures evaluation provenance \(E\) only through free-text annotations, lacking structured verification fields. AI proposed adding a dedicated verification event type to strengthen the E1-E2 mapping.

> **evt\_012, Human rejected**
>
> Premature standardization for v1 of a domain-agnostic standard. What constitutes 'ground truth' and 'verification' varies too widely across domains \(remote sensing vs genomics vs policy analysis\) for a v1 standard to prescribe structured fields. Annotations capture verification narratively and flexibly. v1 should be minimal-and-correct; structured verification templates are future work for domain-specific extensions. \[...\]

### A question that would have primed respondents

*TRACE, April 2026*

> **evt\_011, Decision: agent proposal, rejected by human**
>
> **Agent proposed:** Add Q4b follow-up question asking respondents whether they document the activities they checked in Q4 \(doing-vs-documenting gap measurement\)
>
> **Rationale:** Initial analysis identified that the survey measures activities \(doing\) while the rubric measures documentation quality. AI proposed adding a Q4b to directly measure the doing-vs-documenting gap within the survey instrument.

> **evt\_011, Human rejected**
>
> Adding Q4b would undermine the survey's deliberate anti-priming design. The v2 survey was carefully constructed to avoid revealing the documentation hypothesis until the end screen \(neutralized preamble, topic reveal after completion\). Asking 'do you document this?' mid-survey would prime respondents, contaminating Q6-Q8 with social desirability bias. The doing-vs-documenting gap is measured ACROSS instruments \(survey=practice, audit=documentation\), which is methodologically cleaner than within-survey self-report. \[...\]

### Megatonnes are not metric tons

*proofpress experiments, October 2026*

> **evt\_002, Decision: agent proposal, not yet resolved**
>
> Replace the first Phase 1 key \(report X's reduction targets\) with a scope key: for report X, 2024 Scope 1, Scope 2 market-based, Scope 2 \[...\]

> **evt\_004, Decision: agent proposal, revised by human**
>
> Revise the scope-key proposal so that units, magnitude and patchy reporting are part of the key and the score.

> **evt\_004, Human revised**
>
> Accepted on one condition: the target and base comparisons \(the reduction-target key, its sheet, builder, and scoring\) must remain available to revisit later. The scope key is therefore added alongside the target key, not in place of it; \[...\]

> **evt\_006, Decision: agent proposal, accepted by human**
>
> **Agent proposed:** Stop lowercasing units before comparing them. Both the key builder and the scorer read a unit against an explicit table of known spellings. Case is kept where it carries meaning \(Mt is megatonnes, kt is kilotonnes, Gt is gigatonnes\); case is ignored only in spelled-out words \("Metric Tons", "Million", "tonnes"\). \[...\]
>
> **Rationale:** Lowercasing was there so that formatting differences \("Tonnes" against "tonnes"\) would not count as wrong answers, a problem the toy runs ran into. For units, though, case is part of the meaning: in standard SI prefixes, M is mega and m is milli. Folding case makes megatonnes and metric tons look alike, so magnitude errors can neither be caught nor counted. \[...\]
>
> **Human accepted:** Operator: "i accept this revision. implement this."

> **evt\_008, Contribution: shared idea, AI built**
>
> Scope key for Phase 1: unit reading into tonnes CO2e \(case-aware, ambiguous units refused\), scope key models with a computed total check and \[...\]

Links stored in these records: evt\_004 revises evt\_002; evt\_006 revises evt\_004; evt\_008 builds on evt\_004; evt\_008 builds on evt\_006.

### A required final gate caught an unlocked hot path

*TRACE, May 2026*

> **evt\_028, Contribution: human idea, AI built**
>
> \[...\] Wrapped all 5 knowledge-store RMW spans in extensions/learn/\_\_init\_\_.py \[...\]

> **evt\_036, Correction**
>
> **Correction:** The user-mandated 3-set final gate caught a real defect in my P9\(b\) work. evt\_028 claimed "wrapped all 5 knowledge-store RMW spans". WRONG - there are 6 RMW spans; \`\_recall\_hook\` \(extensions/learn/\_\_init\_\_.py:~97-119\) - the HIGHEST-FREQUENCY path \(core auto-recall, invoked from server.py on session-start/decision-propose/contribution\) - was left UNLOCKED while its tool twin \`trace\_learn\_recall\` and the other 4 spans were locked. Independently corroborated by 2 of 3 final reviewers \(R1 correctness CONDITIONAL \+ R3 reliability CONDITIONAL\); R3 demonstrated a deterministic lost-update \(unlocked \_recall\_hook save clobbers a concurrently-committed locked add → new learning permanently lost\). \[...\]

Links stored in these records: evt\_036 corrects evt\_028.

### Refusing a record that reports itself complete

*RSI-Exam provenance study, September 2026*

> **evt\_006, Decision: agent proposal, rejected by human**
>
> **Agent proposed:** Rejected alternative, recorded for deliberation capture and left for the operator to mark: when the experiment log declares a parent that has no snapshot, drop that parent from parent\_ids silently so the child becomes the lineage root. This would let the Opus probe rollout build a record with zero schema change and would pass the verifier's one-root rule as it stands.
>
> **Rationale:** Considered and set aside in favour of the unsnapshotted\_parent\_ids field. Dropping the parent produces a record that reports itself complete while omitting lineage the log states, which is exactly the fail-open behaviour removed from the producer in pull request \#19 for unrecognised snapshot directories; reintroducing the same class of silent omission one day later, in the lineage the record exists to carry, would undercut the fail-loud discipline the repository is built on. \[...\]

> **evt\_006, Human rejected**
>
> Operator's words on 2026-09-08 \[...\]: "i mean i accept your suggestions. so, i accept 1 and 2 and reject 3." \[...\] Rejected because it would produce a record that reports itself complete while omitting lineage the log plainly states, the same fail-open pattern removed from the producer in pull request \#19.

### The reviewer should not know the answer in advance

*proofpress experiments, October 2026*

> **evt\_020, Decision: human proposal, not yet resolved**
>
> No part of the process, the AI reviewer included, should know the final deliverable \(the closing spreadsheet\) before the last step, so every arm \[...\]

> **evt\_024, Decision: human proposal, accepted by human**
>
> **Human proposed:** Give the ProofPress side's reviewer as few deterministic rules as possible: like a human reviewer, it decides on its own whether and how far to verify each finding, and whether to approve, send back, or reject it, with no rules for specific situations such as chart readings. Record exactly what the reviewer is told, and consider a matching sentence for the Control side's handoff note.
>
> **Rationale:** Operator's words: "there should be less deterministic rules for the reviewer / verifier and it should mainly decide on its own if it wants to verify the claims or not ... it is still listing out so much of what it is supposed to do and even how to handle specific situations \(like the chart reading thing\). but that is in itself hand holding and will bias the proofpress side ... \[...\]
>
> **Human accepted:** Operator accepted the short reviewer text \(role, what each action does, decide every finding before finishing, the safety line; no verify or careful, no rules on figures, years, charts, or wording; no per-figure verdicts\) and settled: the reviewer sees, word for word, the task the session under review was given, never a later step's; \[...\]

> **evt\_026, Contribution: human idea, AI built**
>
> Reviewer setup v4 and session texts v3, built and tested: the reviewer gets its role, what each action does, and the reviewed session's task word for \[...\]

Links stored in these records: evt\_024 revises evt\_020; evt\_026 builds on evt\_020; evt\_026 builds on evt\_024.

### Reversing a scenario rule after building it

*COEQWAL, October 2026*

> **evt\_007, Decision: agent proposal, accepted by human**
>
> **Agent proposed:** Scenario selection follows \[client lead\]'s written rule site-wide: current operations selected by default, the last selected scenario cannot be unselected, and Data in Depth draws exactly the sidebar selection \(its built-in current-operations reference is removed\). \[...\]

> **evt\_013, Decision: human proposal, accepted by human**
>
> **Human proposed:** Scenario selection rule, revised: no "current operations always on". Data in Depth behaves like the other tools: with no scenario selected it shows the select-a-scenario prompt, and it compares only the scenarios the user selected \(no forced current-operations reference\).
>
> **Rationale:** This reverses the Rule A part of evt\_007 \(built locally on feature/current-ops-always-on, never pushed\). On dev and on \#416, Data in Depth also departs from the other tools: it always adds current operations as a reference, even with nothing selected, and never shows the prompt.
>
> **Human accepted:** Oliver stated this as the correct behavior; it replaces the Rule A \("Build A now"\) part of evt\_007.

> **evt\_014, Contribution: human idea, AI built**
>
> PR \#417 into dev: Data in Depth shows the select-a-scenario prompt and compares only the selected scenarios; \[...\]

> **evt\_015, Contribution: human idea, AI built**
>
> Exhaustive Data in Depth live sweep of PR \#417's build: 27 independent per-variable verifier agents \(every location, data view, chart style, compare \[...\]

Links stored in these records: evt\_013 revises evt\_007; evt\_014 builds on evt\_013; evt\_015 builds on evt\_013.

### Tests that could not fail

*COEQWAL, August 2026*

> **evt\_005, Correction**
>
> **Correction:** A high-effort code review of the Task 6 diff caught that my two new Stats-capture assertions were VACUOUS: \`drawer.locator\("svg"\).first\(\)\` matches the share drawer's own MUI close icon, and stageShareItem deliberately swallows capture errors and stages the card anyway, so a totally failed capture would still have passed both tests. The core claim of the PR was untested. Fixed by asserting the capture's own role="img" thumbnail \(SvgThumbnail sets role \+ aria-label from the figure title\), then PROVED the fix by temporarily making the compose branch throw: both assertions went red, and green again on restore. \[...\]

> **ext-1, External reference**
>
> [coeqwal-website pull request 335](https://github.com/berkeley-gif/coeqwal-website/pull/335)

Links stored in these records: evt\_005 corrects ext-1.

### Measure before choosing a retrieval default

*TRACE, October 2026*

> **evt\_002, Decision: agent proposal, accepted by human**
>
> **Human accepted:** Accepted with an added requirement: before implementing, critically investigate why local embedding scores are so low, whether a smaller or larger offline embedding model is right, and how topic/semantic matching is done in comparable systems; calibration values must come from that investigation.

> **evt\_005, Decision: agent proposal, accepted by human**
>
> **Rationale:** Measured on this project's own store \(352 learnings; 100 session-description queries with relevant = learnings extracted from that session; details in evt\_004 and notes/2026-10-12-learn-recall-investigation.md\). No absolute cosine cutoff separates relevant from irrelevant for any model \(best reachable F1 0.10 to 0.16\), and random-pair baselines differ by model \(0.21 to 0.68\), so a per-provider constant would still be wrong on realistic queries. \[...\]
>
> **Human accepted:** Chose "Hybrid ranking \+ retrieval-32M model" over keeping the 8M model or the threshold-only plan.

> **evt\_007, Decision: agent proposal, not yet resolved**
>
> Small-store recall \(fewer than 8 learnings\) returns every learning up to the limit, ranked by the same hybrid fusion as large stores with ties broken \[...\]

> **evt\_009, Decision: agent proposal, not yet resolved**
>
> Decay no longer enters the ordering of candidates with different evidence.

> **evt\_010, Decision: agent proposal, accepted by human**
>
> Default ranking is hybrid only when a transformer embedding provider \(fastembed, default model snowflake-arctic-embed-s with its query prefix\) is \[...\]

> **evt\_011, Contribution: human idea, AI built**
>
> PR \#80 "feat\(learn\): hybrid BM25 \+ embedding recall ranking with a relative floor, decay as tie-breaker, transformer-or-BM25 selection" \(branch \[...\]

Links stored in these records: evt\_005 revises evt\_002; evt\_007 revises evt\_005; evt\_009 revises evt\_005; evt\_010 revises evt\_005; evt\_011 builds on evt\_002; evt\_011 builds on evt\_005; evt\_011 builds on evt\_007; evt\_011 builds on evt\_009; evt\_011 builds on evt\_010.

### The vague cases are the study's subject

*TRACE, March 2026*

> **evt\_005, Decision: agent proposal, accepted by human**
>
> LLM screening implementation plan: 3-tier batched processing \(Tier 1: 479 ambiguous records, Tier 2: 1,073 weak-env records, Tier 3: 1,788 strong-env \[...\]

> **evt\_010, Correction**
>
> **Correction:** AI incorrectly excluded/downgraded 3 papers \(\[1187\], \[1194\], \[294\]\) during intensive audit because their abstracts didn't name specific LLM models - only saying 'artificial intelligence' or 'chatbot'. User corrected: papers that use AI but DON'T clearly document which model or how it was used are EXACTLY the kind of papers this study needs. The vague AI acknowledgment pattern \(scoring 0 on A1 Model Named\) is itself the phenomenon the TRACE paper studies. Inclusion criteria should be: if the paper appears to use AI/LLM as a tool in environmental science, include it even if the specific model isn't named - the poor documentation is a data point, not an exclusion reason. This reframes the screening: the question is 'did they use AI for env sci?' not 'can I confirm they used an LLM specifically?'

Links stored in these records: evt\_010 corrects evt\_005.

### Check that the health checker catches broken setups

*TRACE, August 2026*

> **evt\_003, Contribution: human idea, AI built**
>
> Implemented the conformance layer and the \`trace-mcp doctor\` CLI \[...\]

> **evt\_005, Correction**
>
> **Correction:** A Tier-1 code-review pass over the branch found nine real defects in the conformance probes, all false-negatives - the checker blessing deployments that are actually broken, which matters more than usual because INV-11 makes a clean doctor report load-bearing. The most serious: the hook checks flattened settings.json and discarded the host event, so moving the whole PostToolUse registration block to PreToolUse still reported ok - the decision-audit hook could never fire, which is the very defect INV-11 was minted for. Fixed by deriving the required event per hook from the installer's own settings\_template.json, the same derive-don't-restate rule the rest of the module follows. \[...\]

Links stored in these records: evt\_005 corrects evt\_003.

