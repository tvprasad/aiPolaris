# Insight - AI Engineer Application Package
### Internal Use Only - Prasad Thiriveedi - VPL Solutions LLC

---

## 1. Cover Note

---

I'm a consulting AI engineer with 10+ years of software engineering experience and two years of focused production work building LLM-driven systems on Azure. I'm applying for the AI Engineer role at Insight because the work described - agentic workflows, enterprise API integration, Azure AI platform, client-facing delivery - is exactly what I've been doing.

I build production-grade systems, not prototypes.

**What I've shipped:**

*aiPolaris* is a federal-grade multi-agent orchestration framework - LangGraph DAG with a Planner → Retriever → Synthesizer pipeline, capability-sandboxed tool execution, full audit trail via hashed StepRecords, and Azure Government deployment from a single Terraform workspace switch. Every execution is deterministic and replayable.

*Meridian* is a governed RAG control plane - confidence-calibrated retrieval using isotonic regression, a 12-stage tool execution pipeline with approval-gated write operations, MCP server integration for Claude Desktop, and a ReAct operations agent that uses GPT-4o function calling against live ServiceNow data. 525+ tests. Version 0.16.0 in production.

Both systems run on Azure - Azure OpenAI, Azure AI Search, Azure Container Apps, Entra ID, Key Vault, ADLS Gen2. No hardcoded credentials. Managed identity throughout.

**On the client side:**

My consulting background has put me in rooms with enterprise stakeholders across Fortune 500 environments - translating technical architecture into business outcomes, managing expectations on delivery timelines, and owning the conversation when something breaks. I know how to explain a confidence gate to a compliance officer and a token budget to a CFO.

**On the LangChain question:**

I use LangGraph - the stateful, production-grade agent framework from LangChain Inc. I chose it over LangChain's agent abstractions because explicit state ownership and deterministic execution matter more than convenience when you're deploying to federal environments. Happy to walk through that decision in detail.

I can start two weeks from offer. I work independently, I write clean Python daily, and I've been using Claude Code as my primary AI dev tool throughout both projects.

- Prasad Thiriveedi

---

## 2. Screening Call - Talking Points Map

### Opening (30 seconds)
> "I'm a consulting AI/ML engineer - 10+ years of software engineering, the last two focused entirely on production LLM systems on Azure. I've built two systems from scratch: an agentic orchestration framework and a governed RAG control plane. Both are live. Both run on Azure. I'm looking for the next engagement where I can own a piece of a real platform and ship against real business outcomes."

---

### When they ask about the work (2 minutes)
Lead with Meridian (more relatable to enterprise use cases):

> "Meridian is a governed RAG control plane. An operator asks a question, the system retrieves evidence from a knowledge base, calibrates how confident it is in that evidence, and either answers with citations or refuses with an explanation. Everything is traceable - every execution has a trace ID that you can use to replay it identically months later. It's running on Azure OpenAI, Azure AI Search, with Entra ID auth and managed identity throughout."

Then pivot to aiPolaris:

> "aiPolaris is the orchestration layer - a three-node LangGraph DAG that decomposes a query, retrieves evidence, and synthesizes a cited answer. The design constraint was federal: deterministic, replayable, GCCH-ready, capability-sandboxed. Same codebase deploys to Azure commercial or Azure Government by flipping one Terraform variable."

---

### When they ask about agentic workflows / LangChain

> "I use LangGraph - same organization as LangChain, but it's the stateful graph-based successor. The reason I chose it: in LangChain's agent abstractions, state management is implicit. In LangGraph, every node declares what it owns and what it cannot touch. For a production system where a compliance officer needs to audit every execution, implicit state is a liability. LangGraph gives you explicit ownership, typed state, and deterministic execution. I'd use LangChain if the use case called for it - but for the systems I was building, LangGraph was the right call."

---

### When they ask about Azure

> "Azure is my primary platform. Azure OpenAI for inference, Azure AI Search for hybrid semantic retrieval with reranking, Azure Container Apps for deployment, Entra ID and MSAL for auth, Key Vault for secrets via managed identity, ADLS Gen2 for data staging, Terraform for infrastructure - including workspaces to handle commercial vs. government endpoints. I haven't used AI Foundry directly, but the underlying services are the same ones I've been working with."

---

### When they ask about client-facing experience

> "My consulting background means I've always been in the room with the client. Enterprise environments - large organizations, IT leaders, business stakeholders, compliance teams. The pattern I've found that works: separate the decision from the explanation. When a system refuses to answer a question because confidence is below threshold, the client doesn't need to understand isotonic regression - they need to understand that the system is protecting them from a bad answer. I translate the technical decision into the business outcome, then let them decide whether to adjust the threshold."

---

### When they ask about MLOps / ML lifecycle

> "I run an offline eval harness with golden question sets - p50/p95 latency, correct refusal rate, incorrect refusal rate, follow-up pass rate, replay match rate. Every release requires all gates to pass. Prompts are hash-pinned - any change to a system prompt requires a formal decision record and a CI rebuild. Calibration models are versioned and loaded at startup. Schema migrations run through Alembic with a dry-run check before apply. The lifecycle is: build → eval → gate → release → monitor → recalibrate."

---

### When they ask about the financial / risk / insurance use cases

> "I haven't built in those specific domains, but the engineering pattern is identical. Financial analysis automation - that's a retrieval + reasoning pipeline over financial documents, with citations and confidence gating. Risk modeling workflows - that's an agentic loop that gathers evidence from multiple sources before synthesizing a risk assessment. Insurance quote optimization - that's structured data retrieval feeding an LLM that reasons over policy rules. The domain changes. The architecture - retrieval, reasoning, governance, audit - doesn't. I ramp on domain quickly; the systems thinking transfers directly."

---

### When they ask about working independently

> "Both systems were designed and built by me, from architecture through production deployment. I wrote the ADRs, set the constraints, built the eval harness, and shipped the releases. I work best when the architecture is defined and I own a feature end-to-end - which is exactly what this role describes. I don't need hand-holding, but I do ask the right questions early so I'm not building the wrong thing."

---

### When they ask about AI dev tools

> "I use Claude Code as my primary AI engineering tool - it's my daily driver for everything from planning to implementation to review. I've built custom skills and hooks into it for this project. I've used Copilot and Cursor in prior work. My view: these tools are force multipliers on clarity of thinking, not replacements for it. If you can't explain what you want precisely, the tool produces mediocre output. If you can, it's genuinely fast."

---

### When they ask about rate / availability

> "My range is $90–$120/hour depending on scope and commitment. I can start two weeks from offer. I'm available for remote work with the 10% travel expectation."

---

## 3. Client-Facing Interview Q&A Prep

---

**Q: Tell me about yourself.**

> "I'm a consulting AI engineer with 10+ years in software engineering. For the past two years I've been focused entirely on production LLM systems - building the infrastructure that makes AI reliable, auditable, and deployable in enterprise and federal environments. I've shipped two systems on Azure: an agentic orchestration framework and a governed RAG control plane. Both are in production. I work directly with stakeholders, I own my work end-to-end, and I spend most of my day writing Python."

---

**Q: Walk me through a production AI system you've built.**

> "Meridian is probably the most relevant here. It's a governed RAG control plane - an AI system that answers questions from a knowledge base, but with a governance layer that the enterprise clients required.
>
> The problem it solves: a raw LLM answering questions will hallucinate confidently. In an enterprise environment - financial, compliance, legal - that's a liability. Meridian adds three controls: first, it retrieves evidence before generating an answer, so the model is grounded in documents. Second, it calibrates the confidence in that evidence using a statistical model trained on historical relevance data. Third, it enforces a threshold - if confidence doesn't meet the bar, it refuses and explains why.
>
> Every answer comes with citations. Every execution has a trace ID. A compliance officer can look up any answer given to any user and replay the exact execution months later.
>
> On Azure: Azure OpenAI for the model, Azure AI Search for retrieval, Entra ID for auth, Key Vault for secrets, Container Apps for deployment. Python 3.12, FastAPI, 525 tests."

---

**Q: Have you worked with clients directly? Give me an example.**

> "Yes - consulting has always put me in front of the client. One pattern I've navigated often: a technical decision that the client initially pushes back on.
>
> For example - the confidence threshold. When I explained that the system would refuse to answer some questions, the initial reaction was: 'We don't want a system that says no.' My response was to reframe it: 'You don't want a system that says yes when it shouldn't. A confident wrong answer in a financial context is more expensive than a refusal.' I showed them the refusal logs - what was being refused, why, and what the correct answer would have been. They agreed the refusals were appropriate. We tuned the threshold together based on the data.
>
> That's the client dynamic I've found works: bring the data, explain the tradeoff, let them make the call."

---

**Q: How do you handle a situation where the client wants something that isn't the right technical approach?**

> "I separate the concern from the solution. A client asking for something technically wrong is usually asking because they have a real problem that a better solution can solve - they've just anchored on a specific implementation.
>
> My approach: understand the underlying need first. Then present two paths - what they asked for, with its tradeoffs clearly stated, and what I'd recommend, with the reasoning. I don't argue. I make the tradeoff visible, and I let them decide with full information.
>
> If they choose the path I wouldn't recommend, I implement it well and document the decision. Most of the time, when the tradeoffs are visible, they choose the right path anyway."

---

**Q: How do you explain technical decisions to non-technical stakeholders?**

> "I use the outcome, not the mechanism. A non-technical stakeholder doesn't need to understand isotonic regression - they need to understand that the system has a quality bar and will tell them when it can't meet it.
>
> The pattern I use: What does it do in plain terms? Why was it built this way - what problem does it prevent? When does it activate - what triggers it?
>
> Then I watch their face. If they're nodding, I stop. If they look uncertain, I go one level deeper. The goal is not to impress them with the complexity - it's to give them enough to make a decision or ask the right follow-up."

---

**Q: What's your experience with financial or risk modeling workflows?**

> "Not in those specific domains - I've built in federal/government environments. But the engineering pattern is directly transferable.
>
> Financial analysis automation is a retrieval + reasoning pipeline over structured and unstructured financial data. Risk modeling is an agentic loop that gathers evidence from multiple sources - market data, historical records, external feeds - before synthesizing an assessment. Insurance optimization is LLM reasoning over structured policy rules and customer data.
>
> What I bring to those domains: the governance layer. Any financial AI system that reaches production needs confidence scoring, citation tracking, and an audit trail. That's exactly what I've built. The domain knowledge I ramp on quickly. The infrastructure thinking is already there."

---

**Q: Why are you interested in this role specifically?**

> "Three reasons. First, it's production engineering - not research, not prototypes. I build for real users with real consequences. Second, it's Azure-first - that's my primary platform and I'm deep in it. Third, client-facing. I've found that the most interesting AI engineering problems come out of direct client conversations - when a stakeholder says 'that's not quite right' and you have to understand why before you can fix it. Consulting at this level is where the hard problems are."

---

**Q: What's your LangChain experience?**

> "I use LangGraph - which is built and maintained by LangChain Inc. and is their production-grade stateful agent framework. I made that choice deliberately: LangChain's agent abstractions are convenient, but for production systems that need auditable, deterministic execution, implicit state management is a risk. LangGraph gives you explicit node ownership, typed state, and a compiled graph that you can reason about and test.
>
> I know the LangChain ecosystem well - the chain abstractions, the memory primitives, the tool integration patterns. I could work in a LangChain codebase today. I just wouldn't design a new production system with it when LangGraph exists."

---

**Q: What questions do you have for us?**

> 1. "What does the architecture look like on the client side - are you working within an existing Azure tenant, or building greenfield?"
> 2. "How much of the role is building net-new versus integrating into existing enterprise platforms?"
> 3. "What does the client relationship look like - are engineers embedded with the client team, or is there a PM layer between?"
> 4. "What's the evaluation bar for a successful first 90 days?"
