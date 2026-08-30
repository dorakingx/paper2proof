# Competition Dossier

Last verified: 2026-08-31 JST

This dossier treats the official rules as authoritative over the overview,
FAQ, updates, or submission-form labels. `UNKNOWN` means evidence is still
required; it is not treated as a pass.

## Official sources

| Source | URL | Checked | Finding |
|---|---|---:|---|
| Overview and judging criteria | https://agentsforhumans.devpost.com/ | 2026-08-31 | Five equally listed criteria; live demo and/or AgentCore strengthen Technical Implementation. |
| Official rules | https://agentsforhumans.devpost.com/rules | 2026-08-31 | Submission period, new-work rule, repository/license/video/testing requirements, prizes, bonus. |
| Schedule | https://agentsforhumans.devpost.com/details/dates | 2026-08-31 | Deadline: 2026-09-14 17:00 PDT (2026-09-15 09:00 JST). |
| FAQ | https://agentsforhumans.devpost.com/details/faqs | 2026-08-31 | AWS account required; AgentCore encouraged, not mandatory; Builder ID is the account email. |
| Resources | https://agentsforhumans.devpost.com/resources | 2026-08-31 | Current Strands and AgentCore links; $50 credit request cutoff. |
| Updates | https://agentsforhumans.devpost.com/updates | 2026-08-31 | Make Strands unmistakable, do end-to-end work, protect keys, pitch rather than tutorial. |
| Project gallery | https://agentsforhumans.devpost.com/project-gallery | 2026-08-31 | Gallery not yet published; no current-event entries can be audited publicly. |
| Submission manager | https://devpost.com/submit-to/30317-agents-for-humans-hackathon/manage/submissions | 2026-08-31 | Registration exists per entrant; event project not yet created. |

Official rules were updated 2026-08-12 to remove a hashtag requirement. The
substantive current instruction is to include the exact phrase `Agents for
Humans` in a public builder.aws post title. A stale `#AgentsofFootball` label,
if shown by the form, will not be used.

## Rule audit

| Requirement | Status | Evidence / action |
|---|---|---|
| Entrant is an eligible individual resident in Japan | PASS | Japan is not in the official excluded-jurisdiction list; submitter will select Individual / Japan. Conflict-of-interest self-attestation remains the entrant's responsibility. |
| Project newly created during 2026-08-10–2026-09-14 | PASS | Blank Git repository initialized 2026-08-31; disclosure and Git history preserve provenance. |
| Pre-existing code/work disclosed | PASS | No project code imported; frameworks and Codex use disclosed in `docs/disclosures.md`. |
| Strands Agents SDK is a required core technology | UNKNOWN | Dependency pinned and design fixed; runtime trace evidence pending vertical slice. |
| Agent performs end-to-end real work, not only chat | UNKNOWN | State machine and six-role workflow specified; golden-path run pending. |
| Public GitHub/GitLab/Bitbucket URL | UNKNOWN | GitHub authentication and repo creation pending. |
| All source/assets/setup instructions public | UNKNOWN | Initial source is being created; clean-clone audit pending. |
| MIT or Apache license detectable in repository About | UNKNOWN | MIT file exists locally; detection requires public GitHub audit. |
| README included | PASS | `README.md` exists; final links/results remain pending and labeled. |
| Architecture diagram submitted | UNKNOWN | Source diagram and ≥1920px PNG pending. |
| Public YouTube/Vimeo video ≤5:00 | UNKNOWN | Script and real-product capture pending. |
| Video shows working project + problem + user + importance | UNKNOWN | Must be verified from final upload. |
| AWS Builder ID supplied | UNKNOWN | Exact Builder ID email must be read from authenticated AWS profile; never guessed. |
| Free, unrestricted judging access until 2026-10-08 17:00 PDT | UNKNOWN | Production URL and service-lifetime check pending. |
| Submission materials in English | PASS | Repository and planned submission artifacts use English. |
| Third-party APIs/data/code are licensed and authorized | UNKNOWN | Controlled fixtures will carry provenance; final SBOM/license audit pending. |
| Bonus content public before deadline | UNKNOWN | Three evidence-backed builder.aws articles planned after vertical slice. |
| Devpost status is Submitted | UNKNOWN | Must not change until confirmation screen and submission manager both verify. |

## Dates and internal gates

- AWS $50 promotional credit request cutoff: 2026-09-11 12:00 PT / 2026-09-12 04:00 JST.
- Code freeze: 2026-09-13 23:59 JST.
- Video, articles, and submission package complete: 2026-09-14 12:00 JST.
- Internal Devpost submit: 2026-09-14 21:00 JST.
- Official deadline: 2026-09-15 09:00 JST.
- Judging ends: 2026-10-08 17:00 PDT.

## Credit status

`UNKNOWN`. Do not submit the request twice. Check the registered email and AWS
Billing/Credits view before using the official form.

## Current technical references

| Reference | Checked | Decision |
|---|---:|---|
| https://strandsagents.com/docs/user-guide/concepts/agents/structured-output/ | 2026-08-31 | Use invocation-time `structured_output_model`; deprecated legacy method is prohibited. |
| https://strandsagents.com/docs/user-guide/concepts/agents/hooks/ | 2026-08-31 | Use typed hooks for trace/tool/guardrail evidence. |
| https://strandsagents.com/docs/user-guide/concepts/multi-agent/graph/ | 2026-08-31 | Prefer deterministic graph/workflow semantics over a swarm. |
| https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-using-strands.html | 2026-08-31 | Use `AgentCoreCodeInterpreter`, not host execution. |
| https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html | 2026-08-31 | Current recommended deployment path is AgentCore CLI/CodeZip unless native dependencies require a container. |
| https://pypi.org/project/strands-agents/ | 2026-08-31 | Pin current 1.54.0 (released 2026-08-27). |
| https://pypi.org/project/strands-agents-tools/ | 2026-08-31 | Pin current 0.8.7 (released 2026-08-28); tools package is beta and requires independent review. |
| https://pypi.org/project/bedrock-agentcore/ | 2026-08-31 | Pin current 1.22.0; SDK is marked alpha, so integration tests are mandatory. |

## Known official-text inconsistency

The top of the rules says the 2026-08-12 update removed the hashtag
requirement, while a later scoring paragraph still says “Use hashtag Agents
for Humans in the title.” We follow the updated rule and overview: the exact
plain phrase `Agents for Humans` will appear in every bonus title; no unrelated
hashtag is relied upon.
