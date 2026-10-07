# Reusable AI Prompts

Use these after receiving the official PS. Replace placeholders and provide relevant context.
Never paste secrets or personal data. Verify AI output, follow event AI-use rules, and distinguish facts from assumptions. Request code only after selecting the solution and stack.

## A. Problem Statement Analysis

> Analyze this official PS: [OFFICIAL_PS]. Identify the user, pain point, explicit requirements, potential hidden constraints, smallest viable MVP, risks, and possible innovations. Label inferred constraints and assumptions separately; cite the supplied wording for explicit requirements. List questions the team must clarify.

## B. Idea Generation

> Given [PS_ANALYSIS], [TEAM_SKILLS], [AVAILABLE_TIME], and [EVENT_RULES], generate three realistic solutions optimized for hackathon feasibility and judge impact. Compare concept, innovation, user impact, difficulty, time, demo potential, and risk. Explain tradeoffs without inventing requirements or evidence.

## C. Architecture

> For [SELECTED_SOLUTION], [MVP], [SELECTED_STACK], and [CONSTRAINTS], propose a simple architecture. Describe components, interfaces, data flow, access controls, deployment, and failure handling. Include only components needed for the MVP and flag unresolved decisions.

## D. Task Division

> Divide [MVP_AND_ARCHITECTURE] among [TEAM_MEMBERS_AND_SKILLS] within [AVAILABLE_TIME]. Identify tasks that can run in parallel, owners, dependencies, integration contracts, acceptance criteria, and checkpoints. Balance workload and protect time for testing and demo rehearsal.

## E. Debugging

> Analyze [REDACTED_ERROR], [RELEVANT_CODE], [REPRODUCTION_STEPS], and [EXPECTED_BEHAVIOR]. Identify likely causes and targeted diagnostic checks. Suggest the smallest justified fix and how to verify it. Do not blindly rewrite working code; ask for missing context and preserve unrelated behavior.

## F. Security Review

> Review [PROJECT_FILES_AND_SELECTED_STACK] for exposed secrets, insecure endpoints, authorization gaps, weak validation, and dependency issues. Report file/location, issue type, impact, and remediation. Never reproduce secret values. Separate confirmed findings from concerns needing verification.

## G. Judge Simulation

> Act as a hackathon judge using [OFFICIAL_RUBRIC_IF_AVAILABLE]. Based on [PROJECT_SUMMARY_AND_DEMO], ask difficult questions about requirement fit, innovation, implementation, impact, security, failures, and limitations. Ask one question at a time, critique our answer, and suggest evidence that would strengthen it.

## H. README Generation

> Update [CURRENT_README] using [FINAL_IMPLEMENTED_PROJECT_AND_VERIFIED_COMMANDS]. Describe only implemented features, actual technologies, tested setup instructions, known limitations, and verified links. Flag missing details instead of inventing them. Preserve useful team and hackathon context.

## I. Pitch Generation

> Using [PROJECT_FACTS], [DEMO_FLOW], and [AUDIENCE], draft 30-second, 1-minute, and 3-minute pitches. Cover problem, solution, USP, evidence, and honest limitations. Avoid unsupported claims; keep wording natural and suitable for spoken delivery.

## J. Final Project Review

> Evaluate [IMPLEMENTED_PROJECT], [OFFICIAL_PS_AND_RUBRIC], and [DEMO_AND_PRESENTATION] for innovation, technical implementation, impact, UX, scalability, security, demo quality, and presentation quality. Provide actionable improvements ranked by impact, effort, and risk within [TIME_REMAINING]. Distinguish observed results from unverified claims.
