### Shouldn't it just be the one-liner?

*proofpress experiments, October 2026*

> **Agent proposed:** Next 1 from the 2026-10-27 handoff: replace the per-session shutil.copyfile of each report PDF in src/ppx/runcard.py with a clone-or-copy helper: a copy-on-write clone through clonefile \(macOS, ctypes\) or the FICLONE ioctl \(Linux btrfs/XFS\), falling back to shutil.copyfile on any OSError; \[...\]
>
> **Rationale:** Oliver's words: "is it really necessary to do what you recommended and i just agreed to? shouldnt it just be super simple and that one liner?" The ctypes route adds platform code and constants that can be wrong \(the spike's first getattrlist constants were\) for no gain over cp's built-in fallback; one process per report per session build is negligible.
>
> **Human accepted:** Oliver's mid-turn message directed the simpler form; the AI agreed and built it: clone\_or\_copy in src/ppx/runcard.py \(one cp call, -c on macOS, --reflink=auto elsewhere, check=True\) at the two PDF copy sites \(a sample's reports/\<slug\>.pdf and the report.pdf \[...\]

### The vague cases are the study's subject

*TRACE, March 2026*

> **Correction:** AI incorrectly excluded/downgraded 3 papers \(\[1187\], \[1194\], \[294\]\) during intensive audit because their abstracts didn't name specific LLM models - only saying 'artificial intelligence' or 'chatbot'. User corrected: papers that use AI but DON'T clearly document which model or how it was used are EXACTLY the kind of papers this study needs. The vague AI acknowledgment pattern \(scoring 0 on A1 Model Named\) is itself the phenomenon the TRACE paper studies. Inclusion criteria should be: if the paper appears to use AI/LLM as a tool in environmental science, include it even if the specific model isn't named - the poor documentation is a data point, not an exclusion reason. This reframes the screening: the question is 'did they use AI for env sci?' not 'can I confirm they used an LLM specifically?'

### Megatonnes are not metric tons

*proofpress experiments, October 2026*

> **Agent proposed:** Stop lowercasing units before comparing them. Both the key builder and the scorer read a unit against an explicit table of known spellings. Case is kept where it carries meaning \(Mt is megatonnes, kt is kilotonnes, Gt is gigatonnes\); case is ignored only in spelled-out words \("Metric Tons", "Million", "tonnes"\). \[...\]
>
> **Rationale:** Lowercasing was there so that formatting differences \("Tonnes" against "tonnes"\) would not count as wrong answers, a problem the toy runs ran into. For units, though, case is part of the meaning: in standard SI prefixes, M is mega and m is milli. Folding case makes megatonnes and metric tons look alike, so magnitude errors can neither be caught nor counted. \[...\]
>
> **Human accepted:** Operator: "i accept this revision. implement this."

### The reviewer should not know the answer in advance

*proofpress experiments, October 2026*

> **Human proposed:** Give the ProofPress side's reviewer as few deterministic rules as possible: like a human reviewer, it decides on its own whether and how far to verify each finding, and whether to approve, send back, or reject it, with no rules for specific situations such as chart readings. Record exactly what the reviewer is told, and consider a matching sentence for the Control side's handoff note.
>
> **Rationale:** Operator's words: "there should be less deterministic rules for the reviewer / verifier and it should mainly decide on its own if it wants to verify the claims or not ... it is still listing out so much of what it is supposed to do and even how to handle specific situations \(like the chart reading thing\). but that is in itself hand holding and will bias the proofpress side ... \[...\]
>
> **Human accepted:** Operator accepted the short reviewer text \(role, what each action does, decide every finding before finishing, the safety line; no verify or careful, no rules on figures, years, charts, or wording; no per-figure verdicts\) and settled: the reviewer sees, word for word, the task the session under review was given, never a later step's; \[...\]

### Tests that could not fail

*COEQWAL, August 2026*

> **Correction:** A high-effort code review of the Task 6 diff caught that my two new Stats-capture assertions were VACUOUS: \`drawer.locator\("svg"\).first\(\)\` matches the share drawer's own MUI close icon, and stageShareItem deliberately swallows capture errors and stages the card anyway, so a totally failed capture would still have passed both tests. The core claim of the PR was untested. Fixed by asserting the capture's own role="img" thumbnail \(SvgThumbnail sets role \+ aria-label from the figure title\), then PROVED the fix by temporarily making the compose branch throw: both assertions went red, and green again on restore. \[...\]

### Measure before choosing a retrieval default

*TRACE, October 2026*

> **Human accepted:** Accepted with an added requirement: before implementing, critically investigate why local embedding scores are so low, whether a smaller or larger offline embedding model is right, and how topic/semantic matching is done in comparable systems; calibration values must come from that investigation.
>
> **Rationale:** Measured on this project's own store \(352 learnings; 100 session-description queries with relevant = learnings extracted from that session; details in evt\_004 and notes/2026-10-12-learn-recall-investigation.md\). No absolute cosine cutoff separates relevant from irrelevant for any model \(best reachable F1 0.10 to 0.16\), and random-pair baselines differ by model \(0.21 to 0.68\), so a per-provider constant would still be wrong on realistic queries. \[...\]
>
> **Human accepted:** Chose "Hybrid ranking \+ retrieval-32M model" over keeping the 8M model or the threshold-only plan.

### Refusing a record that reports itself complete

*RSI-Exam provenance study, September 2026*

> **Agent proposed:** Rejected alternative, recorded for deliberation capture and left for the operator to mark: when the experiment log declares a parent that has no snapshot, drop that parent from parent\_ids silently so the child becomes the lineage root. This would let the Opus probe rollout build a record with zero schema change and would pass the verifier's one-root rule as it stands.
>
> **Rationale:** Considered and set aside in favour of the unsnapshotted\_parent\_ids field. Dropping the parent produces a record that reports itself complete while omitting lineage the log states, which is exactly the fail-open behaviour removed from the producer in pull request \#19 for unrecognised snapshot directories; reintroducing the same class of silent omission one day later, in the lineage the record exists to carry, would undercut the fail-loud discipline the repository is built on. \[...\]
>
> **Human rejected:** Operator's words on 2026-09-08, after a clarifying exchange: "i mean i accept your suggestions. so, i accept 1 and 2 and reject 3." His first phrasing, "\(3\) i accept this as well", accepted the recommendation to reject; the clarification removes the ambiguity. \[...\]

### Require a visual check before export

*COEQWAL, July 2026*

> **Correction:** Oliver reviewed the first version of the loading-speed brief and corrected two things: \(1\) wording was too padded for the audience \("two worries turned out to be non-issues" and similar framing removed; brief tightened to timing facts only\); \(2\) required a visual QA pass before export, which caught a real layout bug: the 4.7s value labels on full-width bars overflowed the chart-card edge \(bars rescaled to 84% max so labels always fit inside\). Verified after fixes via full-page screenshots at desktop/narrow widths in light and dark themes.

### One PR, reviewed before it is called done

*proofpress, October 2026*

> **Agent proposed:** ProofPress context-lineage fix design: one PR off origin/main \(fix/context-lineage\). \[...\]
>
> **Human revised:** Human kept the context-lineage design but rejected splitting the follow-ups: one PR must also fix the shadowed admission in review\_v2 and the uneven disclosure filtering in receipt\_v2 / traverse\_graph\_v2, then go through inline adversarial passes and gpt-6.1-sol passes before it is called good to go.

### Check that the health checker catches broken setups

*TRACE, August 2026*

> **Correction:** A Tier-1 code-review pass over the branch found nine real defects in the conformance probes, all false-negatives - the checker blessing deployments that are actually broken, which matters more than usual because INV-11 makes a clean doctor report load-bearing. The most serious: the hook checks flattened settings.json and discarded the host event, so moving the whole PostToolUse registration block to PreToolUse still reported ok - the decision-audit hook could never fire, which is the very defect INV-11 was minted for. Fixed by deriving the required event per hook from the installer's own settings\_template.json, the same derive-don't-restate rule the rest of the module follows. \[...\]

### One sheet instead of four

*proofpress experiments, October 2026*

> **Correction:** The operator cut the scope key workbook down to a single sheet \("Values"\), dropping the How to fill, Reports, and Example sheets the harness had generated, and set a standing rule: hand-filled xlsx files are one sheet unless there is a clear reason for more, because extra sheets clutter the form and make mistakes more likely. Fixed in 33c6f40. The scope sheet is now one sheet, read by column header whatever its name. \[...\]

### A required final gate caught an unlocked hot path

*TRACE, May 2026*

> **Correction:** The user-mandated 3-set final gate caught a real defect in my P9\(b\) work. evt\_028 claimed "wrapped all 5 knowledge-store RMW spans". WRONG - there are 6 RMW spans; \`\_recall\_hook\` \(extensions/learn/\_\_init\_\_.py:~97-119\) - the HIGHEST-FREQUENCY path \(core auto-recall, invoked from server.py on session-start/decision-propose/contribution\) - was left UNLOCKED while its tool twin \`trace\_learn\_recall\` and the other 4 spans were locked. Independently corroborated by 2 of 3 final reviewers \(R1 correctness CONDITIONAL \+ R3 reliability CONDITIONAL\); R3 demonstrated a deterministic lost-update \(unlocked \_recall\_hook save clobbers a concurrently-committed locked add → new learning permanently lost\). \[...\]

