# Reflection Brief — Harness Engineering Capstone

**Name: JOANA MARIE B. SABINO** 
**Date: 10/13/2026**

Replace each `→` with your answer. **Every answer cites at least one artifact from your own runs** — a run ID, file path, token count, claim outcome, or test count. Uncited answers do not pass. 3–6 sentences each unless noted. Paste short artifact snippets where they help.

**Environment**

- Model(s): `claude-haiku-4-5-20251001`
- OS / Python: Linux 12 / Python 3.13.0
- Approx. API spend:  **$0.1267** USD
---

## Part 1 — Per-system

### System 1 — Agentic loop

1. **Loop control.** Quote the `stop_reason` sequence from one trace. Name the file and function that decides continue-vs-stop, and how.
   → In my run 20261013_122535, trace traces/claim_01_kitchen_fire.jsonl shows the stop_reason sequence tool_use -> tool_use -> end_turn across three turns. The continue-versus-stop decision is handled in claims_intake/loop.py:tool_use causes the loop to execute the requested tool and continue, while end_turn terminates the loop; unexpected stop reasons are treated as errors. This trace demonstrates that termination depends on the API's structured stop_reason, rather than searching the assistant's natural-language responds for words such as "done". The final end_turn appears on turn 3 of my own claim_01_kitchen_fire.jsonl artifact.

2. **Anti-pattern.** Name one anti-pattern `test_antipatterns.py` checks for. What would break in your run if the loop used it?
   → One anti-pattern checked by test_antipatterns.py is using "string-membership tests against assistant text to control the loop", such as checking whether "done" appears in a response. The test suite also guards against integer-literal iteration caps and Python branching directly on claim_type. If my claim_01_kitchen_fire.jsonl run had relied on a fixed iteration limit instead of stop_reason, it could have stopped before the model completed the necessary tool interactions or continued unnecessarily after completion. My actual trace shows the desired behavior: two tool_use turns followed by end_turn on turn 3, providing direct evidence that structured model state governed termination. 

3. **Tool design.** Pick two tools with overlapping inputs. How do the descriptions prevent misrouting? What did a structured tool error let the agent do that a generic string would not?
   → I compared classify_claim and assess_severity in claims_intake/tools.py; both accept a rationale, but their descriptions prevent misrouting by defining different responsibilities and ordering. classify_claim commits to a claim type and confidence after enough facts are gathered, while assess_severity assigns a severity bucket after classification based on damage magnitude, injury severity, and coverage limits. The same file returns structured errors containing is_error, error_category, is_retryable, and message; for example, an invalid classification returns a permanent, non-retryable error explaining that claim_type must be one of the supported claim types. This structure lets the agent distinguish whether a failure is transient and worth retrying or permanent and requires correcting the request, instead of having to interpret an unstructured generic error string.

4. **Your numbers.** Quote the turn count and cost for one claim. How does it differ from the README sample, and why?
   → For claim_01_kitchen_fire, my run 20261013_122535 completed in 3 turns with an estimated cost of $0.0121, as recorded in runs/20261013_122535/summary.md. The claim used 9,428 input tokens and 532 output tokens and ended with an escalated outcome. The corresponding claim_01_kitchen_fire.jsonl trace shows the three-turn sequence tool_use → tool_use → end_turn. My results differ from the README sample because this was my own live execution using claude-haiku-4-5-20251001, and live model runs can follow different tool-call paths and consume different numbers of tokens.

### System 2 — Context strategy

5. **The reduction.** From `budget.json`: baseline tokens, assembled tokens, reduction %. Which section dominates the assembled context, and why keep it verbatim?
   → From my budget.json, the baseline context was 38,708 tokens, while the assembled context was 16,778 tokens, giving a 56.65% reduction. The active section dominates the assembled context at 15,789 tokens, compared with only 204 tokens for case facts, 388 for the resolved refund, and 415 for the resolved subscription. The active section is kept verbatim because it represents the current unresolved conversation, where preserving the exact details avoids information loss that could occur through summarization. In contrast, the two resolved issues can be compressed because their important outcomes have already been captured in concise summaries.

6. **Summarize vs preserve.** State the rule for what gets summarized vs kept byte-exact, citing your per-section token numbers.
   → The rule is to summarize resolved issues but preserve the active issue byte-exact, because resolved conversations mainly need their outcomes and key facts, while the unresolved issue still requires the full conversational detail. In my runs/20261013-130604/budget.json, the resolved refund was compressed to 388 tokens and the resolved subscription to 415 tokens, while the active payment-method issue remained at 15,789 tokens; the case-facts block used another 204 tokens. My runs/20261013-130604/context.md confirms this structure: the refund and subscription appear as concise Outcome → Key facts → Resolution summaries, whereas the active payment-method section preserves the detailed conversation from Turn 29 through Turn 48. This approach reduces historical context while retaining maximum fidelity for the issue that is still in progress.

7. **Facts block.** Compare `eval.jsonl` to `eval_control.jsonl`. Which question regressed, and what does that prove?
   → Comparing my eval.jsonl with eval_control.jsonl, Q6 regressed from pass to fail when the case-facts block was removed. In eval.jsonl, Q6 correctly returned the exact structured status in_progress, while in eval_control.jsonl the model answered that the status was unknown because no exact status token was available. Q1 still passed in the control because the $22.14 refund amount was also preserved in the resolved refund summary. This proves that the case-facts block is load-bearing for certain structured facts, especially exact status tokens that may not appear verbatim in the summarized or active conversation.

### System 3 — Claude Code config

8. **Path-scoped rules.** Quote the glob frontmatter from one rule file. Why is it better than a directory-level CLAUDE.md for cross-cutting conventions?
   → In .claude/rules/tests.md, the path-scoped rule uses the glob frontmatter: 
   paths:
  - "**/*.test.tsx"
  - "**/*.test.ts"
---
   These globs apply the testing conventions to matching test files anywhere in the repository, including co-located tests that may sit alongside React or API code. The same artifact states that the test rules can apply on top of React or API rules when appropriate. This is better than a directory-level CLAUDE.md for cross-cutting conventions because the rule follows the file pattern rather than a single directory, allowing one consistent testing standard across the monorepo.

9. **Forked skill.** Quote the `context: fork` and `allowed-tools` lines. What does running forked + read-only buy you? What breaks without it?
   → In .claude/skills/deploy-check/SKILL.md, the skill declares:
   context: fork
   allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git rev-parse:*)
  - Bash(git ls-files:*)
  - Bash(gh pr view:*)
  - Bash(gh pr checks:*)

   Running in a fork keeps verbose file enumeration, diff parsing, and Git output out of the main session, returning only the structured pass/fail summary. The restricted allowlist keeps the validation read-only, so it cannot modify files, push changes, run migrations, or deploy. Without the fork, the main context would be polluted by low-value intermediate output; without the allowlist, the deploy check would lose its enforced safety boundary and could gain unintended write or deployment capabilities.

10. **Scope.** From the validator output: project-level vs user-level scope. Give one example of each from this config.
    → Running python -m ecommerce_team_config . on my System 3 configuration returned OK, confirming that the configuration hierarchy passed validation. A project-level example is .claude/skills/deploy-check/SKILL.md, which is part of the repository and defines the shared /deploy-check workflow for the team. A user-level example documented in that same skill is ~/.claude/skills/deploy-check-strict/, which is intended for a stricter personal variant that does not affect teammates or get committed to the repository. This separation keeps shared project behavior consistent while allowing individual preferences to remain local.

### System 4 — Orchestration

11. **Push work down.** Defects the SQL query returned vs warm-tier total. Name the indexed query. Why does the model never see the full history?
    → My data/warm.sqlite contained 40 total defects, while the current shift's indexed SQL query returned 0 new defects, as recorded in data/shift_scratchpad.jsonl: "0 new defects analyzed since 2026-10-13T05:33:45Z". The indexed query is defects_since() in shift_monitor/warm.py, which runs SELECT * FROM defects WHERE ts > ? ORDER BY ts DESC LIMIT ? using the idx_defects_ts index on defects(ts). In shift_monitor/pipeline.py, this query runs before build_rich_prompt(), and only the resulting new_defects list is supplied to the prompt builder. Therefore, the model never sees the full 40-record history because SQLite performs the timestamp filtering, ordering, and limiting before the model call.

12. **Crash recovery.** The resume-vs-fresh decision and its staleness threshold (`recovery.py`). Why is a fresh start with an injected summary sometimes more reliable than resuming?
    → In shift_monitor/recovery.py, the recovery logic uses a 30-minute staleness threshold (STALE_RESUME_THRESHOLD_MINUTES = 30). An incomplete run is resumed only when its last recorded step is no more than 30 minutes old; runs with no steps, completed runs, or incomplete runs older than 30 minutes receive a fresh start. The file explains that a fresh start uses whatever findings the manifest has already captured as an injected summary. This can be more reliable than resuming because an older partial run is treated as stale, while the fresh invocation starts from the durable findings already recorded instead of continuing an outdated working context.

13. **Small state.** Byte size of your `hot_state.json`. Why does the budget matter for a system run once per shift, indefinitely?
    → My generated data/hot_state.json is 643 bytes, well within the configured 5,120-byte (~5 KB) HOT_STATE_BYTE_BUDGET in shift_monitor/state.py. The implementation enforces the limit when writing the state and raises an error if the serialized payload exceeds the budget; pipeline.py also uses _trim_to_budget() to reduce active_alerts when necessary. The budget matters because the system runs once per shift indefinitely, so without a fixed bound the persistent working state could continually accumulate information across shifts. Keeping hot state bounded ensures that every future prompt receives a compact operational state instead of an ever-growing history.

---

## Part 2 — Synthesis

*Graded on connecting two or more systems. Cite a named file/artifact from each.*

14. **Three layers.** Point to a file/artifact for each layer and justify.
    → Model: runs/20261013_122535/traces/claim_01_kitchen_fire.jsonl represents the model layer because it records the model’s decisions across three turns: tool_use → tool_use → end_turn.
    → Harness: claims_intake/tools.py and claims_intake/loop.py represent the harness layer because they define the model’s available actions, execute tool calls, return structured errors, and interpret stop_reason.
    → Orchestration: shift_monitor/pipeline.py, data/warm.sqlite, and data/hot_state.json represent the orchestration layer because they retrieve cross-shift state, build each invocation, call the model, and persist the updated state. Together, these artifacts separate model reasoning from per-call control and long-running state coordination.

15. **Deterministic vs prompt.** Cite one behavior guaranteed in code (terminal tool, read-only allowlist, atomic write, byte budget) and one guided by prompt. When is each right?
    → A behavior guaranteed in code is the 5,120-byte hot-state limit in shift_monitor/state.py; write_atomic() rejects oversized state and uses a temporary file plus os.replace() for atomic persistence. A prompt-guided behavior is the model’s selection of tools such as classify_claim, assess_severity, or escalate_to_human, whose usage is directed by the descriptions in claims_intake/tools.py; my claim_01_kitchen_fire.jsonl trace shows the resulting model-controlled path. Deterministic enforcement is appropriate for safety and integrity properties that must always hold, such as storage limits and atomic writes. Prompt guidance is appropriate for semantic decisions that depend on interpreting claim facts but must remain inside a constrained tool interface.

16. **Context, two faces.** Compare context management in System 2 (intra-session) and System 4 (cross-session) with cited numbers from both. Same principle, different mechanism — how?
    → System 2 manages context within a session: budget.json reduced the baseline from 38,708 tokens to 16,778 tokens, a 56.65% reduction, by compressing resolved issues while preserving the 15,789-token active section. System 4 manages context across sessions: data/hot_state.json is only 643 bytes, against the 5,120-byte limit defined in shift_monitor/state.py, while the full 40-defect history remains in data/warm.sqlite. Both systems follow the same principle of carrying forward only information needed for the next decision. System 2 accomplishes this through summarization and byte-exact preservation, while System 4 uses storage tiers, SQL retrieval, and a bounded persistent state.

17. **Reliability you can't see in one run.** Name one behavior a test guarantees that a single successful run would not reveal. Why does it matter before shipping?
    → test_antipatterns.py guarantees that the System 1 loop does not use natural-language string matching, a hard-coded iteration cap, or Python-level claim_type branching as its primary decision mechanism. A single successful trace such as claim_01_kitchen_fire.jsonl only proves that one claim completed in three turns; it cannot prove that an unexecuted code path lacks those anti-patterns. The AST-based test examines the source structure even when the problematic path is not reached during a run. This matters before shipping because one successful outcome does not establish that architectural control rules hold across the entire implementation.

18. **Blast radius.** Pick one system. What's the blast radius if it misbehaves, and what's the kill switch? Ground it in that system's tools, enforcement points, and state.
    → I chose System 3’s /deploy-check skill because its blast radius is explicitly constrained by .claude/skills/deploy-check/SKILL.md. The skill runs with context: fork and allows only Read, Grep, Glob, selected read-only Git commands, and GitHub PR/check inspection; it cannot write files, push commits, run migrations, or deploy. Its main possible failure is therefore an incorrect pass/fail recommendation or excessive diagnostic work, rather than a direct production modification, and the fork keeps intermediate output outside the main session. The practical kill switch is to stop invoking or disable the project-scoped /deploy-check skill, while the allowed-tools list remains the primary enforcement point that limits what the skill can do.

---

## Part 3 — Honest assessment

19. **What broke.** One thing that failed first try in your environment, and how you fixed it. (If nothing, what you checked to be sure.)
    → My first attempt failed because I had not created/configured the required .env file, so I was unable to successfully complete the initial environment setup and run pip install -e ".[dev]" as intended. I fixed the issue by adding the required .env configuration and then rerunning the setup command. After correcting the environment configuration, I was able to proceed with installing the development dependencies and running the system exercises. This reinforced that environment configuration is a prerequisite worth validating before troubleshooting the application code itself.

20. **What you'd change.** One architectural decision you'd make differently, grounded in what you observed.
    → If I were designing the project again, I would make the boundary between Claude and the harness clearer from the beginning. From these exercises, I learned that Claude is most useful for flexible reasoning and decisions, while the harness should enforce predictable rules such as tool permissions, validation, error handling, and state limits. For example, .claude/skills/deploy-check/SKILL.md restricts the available tools, while shift_monitor/state.py enforces the 5,120-byte state budget in code. I would structure future Claude SDK and Claude Code projects around this separation earlier, so the AI remains flexible without making critical system behavior depend only on prompts.
