# Cognitive Multi-Agent System for Dynamic B2B Sales Automation

> **Version:** 1.0 · **Date:** 2026-09-26  
> **Authors:** Shubham (Architecture & AI Pipeline), Lavanya (Communications & Outreach), Akshat (Orchestration & Scoring)  
> **Status:** Research Architecture — Active Development

---

## Abstract

This document describes **MASAA** (Multi-Agent Sales Automation Architecture) — a cognitive multi-agent system for automating the end-to-end B2B sales pipeline. Unlike conventional CRM automation that relies on static rule-based workflows, MASAA employs **seven specialised agents** with a **three-tier memory architecture** (working, episodic, semantic), coordinated by an **industry-adaptive orchestrator** that reconfigures its behaviour based on domain-specific **Industry Knowledge Packs (IKPs)**.

The system is designed to handle Finance, IT/SaaS, B2B Manufacturing, and Supply Chain verticals out of the box, with a pluggable IKP framework that allows extension to any industry without code changes.

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Memory Architecture](#3-memory-architecture)
4. [The Seven Agents](#4-the-seven-agents)
5. [Industry Knowledge Packs (IKPs)](#5-industry-knowledge-packs-ikps)
6. [Orchestrator Design](#6-orchestrator-design)
7. [Lead Lifecycle State Machine](#7-lead-lifecycle-state-machine)
8. [Agent Communication Protocol](#8-agent-communication-protocol)
9. [LLM Gateway & Reasoning Layer](#9-llm-gateway--reasoning-layer)
10. [Data Model](#10-data-model)
11. [API Design](#11-api-design)
12. [Security & Compliance](#12-security--compliance)
13. [Evaluation Framework](#13-evaluation-framework)
14. [Implementation Roadmap](#14-implementation-roadmap)
15. [Team Integration Contracts](#15-team-integration-contracts)

---

## 1. Design Philosophy

### 1.1 Why Multi-Agent?

A monolithic sales bot fails because B2B sales is not one task — it is a **coalition of specialised reasoning problems**: intelligence gathering requires different skills than relationship mapping, which requires different skills than message crafting. Each agent brings a specialised cognitive capability:

| Problem | Required Capability | Agent |
|---|---|---|
| Finding the right companies to sell to | Web intelligence, data fusion | Intelligence Agent |
| Understanding a company deeply | Research synthesis, pattern extraction | Profiler Agent |
| Identifying who to talk to | Org-chart reasoning, social graph analysis | Relationship Mapper |
| Deciding the right approach | Strategic reasoning, historical learning | Strategy Agent |
| Crafting the right message | Persuasion, personalisation, tone control | Communication Agent |
| Reading responses and adapting | Sentiment analysis, intent classification | Sentiment Agent |
| Coordinating everything | Planning, scheduling, conflict resolution | Orchestrator |

### 1.2 Core Principles

1. **Agents are specialists, not generalists.** Each agent has a narrow, well-defined competency. No agent tries to do everything.

2. **Memory drives intelligence.** Without memory, agents are stateless function calls. With episodic memory ("Company X responded well to ROI-focused messaging last quarter") and semantic memory ("Fintech buyers care about compliance first"), agents exhibit adaptive behaviour.

3. **Industry configuration, not industry code.** The same agent codebase serves Finance, IT, B2B, and Supply Chain — behaviour differences are driven by declarative Industry Knowledge Packs, not if/else branches.

4. **Human-in-the-loop is a feature, not a limitation.** The system surfaces recommendations and drafts; humans approve high-stakes actions. The approval gate is a first-class architectural element, not an afterthought.

5. **Every claim has provenance.** When the system says "This company has 200 employees," it cites the source URL, extraction method, and confidence score. No hallucinated data enters the CRM.

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND LAYER                                 │
│              React Dashboard  ·  REST API  ·  WebSocket (live)              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │    ORCHESTRATOR AGENT        │
                    │  (Industry-Adaptive Router)  │
                    │                              │
                    │  ┌────────────────────────┐  │
                    │  │ Industry Knowledge Pack │  │
                    │  │ (Finance│IT│B2B│Chain)  │  │
                    │  └────────────────────────┘  │
                    └──┬───┬───┬───┬───┬───┬──────┘
                       │   │   │   │   │   │
         ┌─────────────┘   │   │   │   │   └─────────────┐
         ▼                 ▼   │   ▼   ▼                  ▼
  ┌─────────────┐  ┌──────────┐│┌──────────┐  ┌──────────────────┐
  │ INTELLIGENCE│  │ PROFILER ││ │ STRATEGY │  │  COMMUNICATION   │
  │   AGENT     │  │  AGENT   │││  AGENT   │  │     AGENT        │
  │             │  │          │││          │  │                  │
  │ Lead disc.  │  │ Deep     │││ Approach │  │ Email·WhatsApp   │
  │ Data fusion │  │ research │││ planning │  │ Call·Telegram    │
  │ Multi-source│  │ Profile  │││ Playbook │  │ LinkedIn·Insta   │
  └──────┬──────┘  └────┬─────┘│└────┬─────┘  └───────┬──────────┘
         │              │      │     │                 │
         │       ┌──────▼──────┐     │          ┌──────▼──────┐
         │       │ RELATIONSHIP│     │          │  SENTIMENT  │
         │       │   MAPPER    │     │          │   AGENT     │
         │       │             │     │          │             │
         │       │ Org charts  │     │          │ Response    │
         │       │ Buyer comm. │     │          │ analysis    │
         │       │ Stakeholders│     │          │ Intent det. │
         │       └──────┬──────┘     │          └──────┬──────┘
         │              │            │                 │
         ▼              ▼            ▼                 ▼
  ┌───────────────────────────────────────────────────────────────┐
  │                      BLACKBOARD (Shared State)                │
  │              Inter-agent message bus + event log               │
  └───────────────────────────┬───────────────────────────────────┘
                              │
  ┌───────────────────────────▼───────────────────────────────────┐
  │                      MEMORY LAYER                              │
  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
  │  │   WORKING    │  │   EPISODIC   │  │      SEMANTIC        │ │
  │  │   MEMORY     │  │   MEMORY     │  │      MEMORY          │ │
  │  │             │  │              │  │                      │ │
  │  │ Current ctx │  │ Interaction  │  │ Industry knowledge   │ │
  │  │ Active lead │  │ history per  │  │ Buyer personas       │ │
  │  │ Session buf │  │ lead/company │  │ Objection patterns   │ │
  │  │ (ephemeral) │  │ (persistent) │  │ Channel performance  │ │
  │  └─────────────┘  └──────────────┘  │ (persistent+evolving)│ │
  │                                      └──────────────────────┘ │
  └───────────────────────────┬───────────────────────────────────┘
                              │
  ┌───────────────────────────▼───────────────────────────────────┐
  │                      LLM GATEWAY                               │
  │         Groq (fast) → Gemini (deep) → Mock (fallback)         │
  │         Prompt registry · Token budgeting · Caching            │
  └───────────────────────────┬───────────────────────────────────┘
                              │
  ┌───────────────────────────▼───────────────────────────────────┐
  │                     PERSISTENCE LAYER                          │
  │          SQLAlchemy ORM · SQLite (dev) · PostgreSQL (prod)     │
  │          13 tables · Full audit trail · Evidence provenance    │
  └───────────────────────────────────────────────────────────────┘
```

---

## 3. Memory Architecture

The memory system is inspired by cognitive science models (Atkinson-Shiffrin 1968, Tulving 1972) adapted for multi-agent coordination. Each memory tier serves a distinct purpose and has different persistence, scope, and access patterns.

### 3.1 Working Memory (Short-Term)

**Analogy:** What you're thinking about right now.

**Purpose:** Holds the active context for the current agent operation. When the Intelligence Agent is researching "Razorpay," working memory contains the search queries tried so far, the URLs visited, partial results, and the current reasoning chain.

**Properties:**
- **Scope:** Single agent, single lead, single operation
- **Lifetime:** Discarded after the operation completes
- **Size:** Bounded (configurable token window, default 4K tokens)
- **Storage:** In-memory (Python dataclass)

```python
@dataclass
class WorkingMemory:
    """Per-operation scratchpad for an agent."""
    lead_id: int
    agent_name: str
    started_at: datetime

    # Reasoning trace
    observations: List[str]        # "Found 3 job postings mentioning 'Series B'"
    hypotheses: List[str]          # "Company is likely in growth phase"
    decisions: List[str]           # "Will prioritize CTO over VP Engineering"
    
    # Intermediate data
    search_queries_tried: List[str]
    urls_visited: List[str]
    partial_results: Dict[str, Any]
    
    # Token budget tracking
    tokens_used: int = 0
    token_budget: int = 4096
```

### 3.2 Episodic Memory (Interaction History)

**Analogy:** Personal experiences — "The last time I called this client, they said X."

**Purpose:** Records every interaction with a specific lead or company, timestamped and attributed. Enables agents to learn from past interactions: what messaging worked, what objections were raised, what channels got responses.

**Properties:**
- **Scope:** Per-lead (shared across all agents)
- **Lifetime:** Persistent (survives restarts, never deleted)
- **Size:** Unbounded (with summarisation for old entries)
- **Storage:** Database (SQLite/PostgreSQL)

```python
class EpisodicMemory(Base):
    """Records interactions and outcomes for a specific lead."""
    __tablename__ = "episodic_memory"

    id: int                        # PK
    lead_id: int                   # FK → leads
    agent_name: str                # which agent created this memory
    event_type: str                # OUTREACH_SENT | RESPONSE_RECEIVED | MEETING_SCHEDULED | ...
    
    channel: str                   # email | whatsapp | call | linkedin | ...
    content_summary: str           # LLM-generated summary of the interaction
    raw_content: str               # full text (email body, call transcript, etc.)
    
    outcome: str                   # POSITIVE | NEGATIVE | NEUTRAL | NO_RESPONSE
    sentiment_score: float         # -1.0 to 1.0
    
    key_signals: JSON              # ["mentioned_budget", "asked_for_demo", "raised_compliance_concern"]
    lessons_learned: str           # LLM-generated: "This buyer responds better to data-driven pitches"
    
    created_at: datetime
```

**Usage by Agents:**
- **Communication Agent:** "Last email to this lead used ROI messaging and got no response. Try compliance-focused messaging this time."
- **Strategy Agent:** "This lead has been contacted 3 times with no response. Recommend channel switch from email to LinkedIn."
- **Sentiment Agent:** "Response tone has shifted from neutral to positive over the last 2 interactions. Recommend escalating to demo request."

### 3.3 Semantic Memory (Domain Knowledge)

**Analogy:** General world knowledge — "Fintech companies care about PCI-DSS compliance."

**Purpose:** Stores industry knowledge, buyer personas, objection-handling playbooks, and performance statistics that agents use for reasoning. This is the system's "expertise." It evolves over time as the system learns which approaches work.

**Properties:**
- **Scope:** Global (shared across all leads)
- **Lifetime:** Persistent, versioned, and evolving
- **Size:** Structured (knowledge graph + embeddings)
- **Storage:** Database + optional vector store for similarity search

```python
class SemanticMemory(Base):
    """Domain knowledge the system has learned or been taught."""
    __tablename__ = "semantic_memory"

    id: int
    category: str                  # INDUSTRY_KNOWLEDGE | BUYER_PERSONA | OBJECTION_PATTERN |
                                   # CHANNEL_PERFORMANCE | MESSAGING_TEMPLATE | COMPLIANCE_RULE
    industry: str                  # "finance" | "it_saas" | "b2b_manufacturing" | "supply_chain" | "*"
    
    knowledge_key: str             # unique identifier within category
    knowledge_value: JSON          # structured knowledge content
    
    source: str                    # "ikp_default" | "learned_from_data" | "user_provided"
    confidence: float              # 0.0–1.0, decays over time for learned knowledge
    times_applied: int             # how often this knowledge was used in decisions
    times_successful: int          # how often the decision led to a positive outcome
    success_rate: float            # computed: times_successful / times_applied
    
    created_at: datetime
    updated_at: datetime
    version: int                   # for tracking knowledge evolution
```

**Examples of stored knowledge:**

```json
// Category: BUYER_PERSONA
{
  "knowledge_key": "finance_cfo_persona",
  "knowledge_value": {
    "role": "CFO",
    "industry": "finance",
    "priorities": ["cost_reduction", "regulatory_compliance", "risk_management"],
    "pain_points": ["manual_reconciliation", "audit_preparation", "cash_flow_visibility"],
    "preferred_channels": ["email", "linkedin"],
    "messaging_tone": "data_driven_formal",
    "typical_objections": ["budget_freeze", "existing_vendor", "implementation_risk"],
    "decision_timeline": "2-6 months",
    "buying_committee": ["CFO", "VP Finance", "Head of Procurement", "IT Security"]
  }
}

// Category: CHANNEL_PERFORMANCE (learned from data)
{
  "knowledge_key": "email_vs_linkedin_it_saas",
  "knowledge_value": {
    "industry": "it_saas",
    "email_response_rate": 0.12,
    "linkedin_response_rate": 0.23,
    "whatsapp_response_rate": 0.08,
    "recommendation": "linkedin_first_then_email",
    "sample_size": 347
  },
  "source": "learned_from_data",
  "confidence": 0.82
}
```

### 3.4 Memory Interaction Patterns

```
                    ┌─────────────────────────────────┐
                    │        AGENT EXECUTION           │
                    └──────────┬──────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
      ┌───────────┐    ┌────────────┐    ┌───────────┐
      │  RECALL   │    │  REASON    │    │  RECORD   │
      │           │    │            │    │           │
      │ Load      │    │ Use domain │    │ Save new  │
      │ episodic  │    │ knowledge  │    │ episodic  │
      │ history   │    │ + history  │    │ memory    │
      │ for this  │    │ to make    │    │ + update  │
      │ lead      │    │ decisions  │    │ semantic  │
      │           │    │            │    │ stats     │
      └───────────┘    └────────────┘    └───────────┘
      (Episodic)       (Semantic +       (Episodic +
                        Working)          Semantic)
```

**Before each agent runs:** Load relevant episodic memories for the lead + relevant semantic knowledge for the industry.

**During execution:** Working memory holds the agent's current reasoning chain.

**After execution:** Record the interaction as episodic memory. Update semantic memory statistics (was this approach successful?).

---

## 4. The Seven Agents

### 4.1 Intelligence Agent

**Role:** Lead Discovery & Data Fusion  
**Handles States:** `NEW`  
**Outputs To:** `INTELLIGENCE_GATHERED`

The Intelligence Agent does NOT just scrape Google Maps. It is a **multi-source data fusion engine** that cross-references information from:

| Source | Data Extracted | Confidence |
|---|---|---|
| Company registries (MCA/ROC for India, SEC for US) | Legal name, directors, incorporation date, revenue | 0.95 |
| LinkedIn Company Pages | Employee count, industry, headquarters, key people | 0.85 |
| Crunchbase / AngelList | Funding rounds, investors, growth stage | 0.90 |
| News (Google News, industry press) | Recent events, expansions, pain signals | 0.70 |
| Job postings (LinkedIn, Indeed) | Tech stack, hiring signals, growth indicators | 0.75 |
| Official website (discovered, not assumed) | Products, services, contact info, team | 0.85 |
| Google Maps / Business listings | Address, phone, ratings, opening hours | 0.80 |
| Social media presence | Brand maturity, engagement, content themes | 0.65 |

**Key Innovation: Confidence-Weighted Data Fusion**

When multiple sources provide conflicting data (e.g., LinkedIn says 50 employees, Crunchbase says 80), the Intelligence Agent doesn't pick one arbitrarily. It applies **confidence-weighted fusion**:

```
fused_value = Σ(source_value × source_confidence × recency_weight) / Σ(confidence × recency)
```

Every piece of data carries an `Evidence` record with source URL, extraction method, confidence score, and timestamp.

```python
class IntelligenceAgent(BaseAgent):
    name = "intelligence_agent"
    handles_states = {LeadState.NEW}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        # 1. RECALL: Check if we have recent intelligence on this company
        episodic = await self.memory.recall_episodic(ctx.lead_id, event_type="INTELLIGENCE_GATHERED")
        if episodic and episodic.is_fresh(hours=72):
            return AgentResult(status=SKIPPED, message="Recent intelligence exists.")
        
        # 2. GATHER: Multi-source collection
        sources = await asyncio.gather(
            self.search_web(ctx.lead_data["company_name"], ctx.lead_data["location"]),
            self.search_linkedin(ctx.lead_data["company_name"]),
            self.check_company_registry(ctx.lead_data["company_name"]),
            self.scan_news(ctx.lead_data["company_name"]),
            self.scan_job_postings(ctx.lead_data["company_name"]),
        )
        
        # 3. FUSE: Cross-reference and resolve conflicts
        fused_profile = self.confidence_weighted_fusion(sources)
        
        # 4. RECORD: Store as episodic memory
        await self.memory.record_episodic(ctx.lead_id, "INTELLIGENCE_GATHERED", fused_profile)
        
        return AgentResult(
            status=SUCCESS,
            next_state=LeadState.INTELLIGENCE_GATHERED,
            artifacts={"evidence": fused_profile.evidence_records}
        )
```

### 4.2 Profiler Agent

**Role:** Deep Company Research & Profile Building  
**Handles States:** `INTELLIGENCE_GATHERED`  
**Outputs To:** `PROFILED`

Goes beyond raw data — uses LLM reasoning to build a **structured company narrative**:

- **Business Model Analysis:** Is this a B2B SaaS? Agency? Manufacturer? What's their revenue model?
- **Growth Stage Classification:** Startup / Growth / Mature / Declining (based on funding, hiring, news signals)
- **Technology Stack Inference:** From job postings, website tech, and integrations mentioned
- **Pain Point Hypothesis:** Based on industry knowledge + company signals, what problems likely keep their leadership awake?
- **Competitive Positioning:** Where do they sit in their market? Who are their competitors?

```python
class ProfilerAgent(BaseAgent):
    name = "profiler_agent"
    handles_states = {LeadState.INTELLIGENCE_GATHERED}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        # Load semantic knowledge for this industry
        industry_knowledge = await self.memory.recall_semantic(
            category="INDUSTRY_KNOWLEDGE",
            industry=ctx.lead_data["industry"]
        )
        
        # LLM-powered analysis
        profile = await self.llm.generate_json(
            prompt=self._build_analysis_prompt(ctx, industry_knowledge),
            system_prompt=PROFILER_SYSTEM_PROMPT
        )
        
        return AgentResult(
            status=SUCCESS,
            next_state=LeadState.PROFILED,
            artifacts={"company_profile": profile}
        )
```

### 4.3 Relationship Mapper Agent

**Role:** Decision-Maker Identification & Stakeholder Mapping  
**Handles States:** `PROFILED`  
**Outputs To:** `RELATIONSHIPS_MAPPED`

The biggest reason B2B sales fail is **talking to the wrong person**. This agent identifies:

- **Buying Committee:** Who are the decision-makers, influencers, and gatekeepers?
- **Organisational Hierarchy:** Inferred from LinkedIn, company website team pages, news mentions
- **Champion Identification:** Who inside the target company is most likely to advocate for our solution?
- **Contact Prioritisation:** Ranked list of who to reach out to first, second, third

Uses semantic memory buyer personas to match roles to the IKP's `typical_buyer_roles`.

```python
class RelationshipMapperAgent(BaseAgent):
    name = "relationship_mapper"
    handles_states = {LeadState.PROFILED}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        # Get buyer persona for this industry from semantic memory
        personas = await self.memory.recall_semantic(
            category="BUYER_PERSONA",
            industry=ctx.lead_data["industry"]
        )
        
        # Identify key people from evidence (LinkedIn, website team page, news)
        people = self._extract_people_from_evidence(ctx.evidence)
        
        # Match people to buyer roles using LLM
        stakeholder_map = await self.llm.generate_json(
            prompt=self._build_mapping_prompt(people, personas, ctx),
            system_prompt=RELATIONSHIP_MAPPER_SYSTEM_PROMPT
        )
        
        return AgentResult(
            status=SUCCESS,
            next_state=LeadState.RELATIONSHIPS_MAPPED,
            artifacts={"stakeholder_map": stakeholder_map}
        )
```

### 4.4 Strategy Agent

**Role:** Approach Planning & Playbook Selection  
**Handles States:** `RELATIONSHIPS_MAPPED`  
**Outputs To:** `STRATEGY_SET`

This is where the system's **strategic intelligence** lives. The Strategy Agent:

1. Loads the **Industry Knowledge Pack** for the target's industry
2. Queries **episodic memory** for past interactions with similar companies
3. Queries **semantic memory** for channel performance data and objection patterns
4. Uses LLM reasoning to produce an **Approach Plan**:

```json
{
  "approach_plan": {
    "primary_contact": "Rajesh Sharma, CTO",
    "opening_channel": "linkedin",
    "follow_up_channel": "email",
    "messaging_angle": "compliance_automation",
    "tone": "consultative_technical",
    "key_value_props": [
      "Reduce audit preparation time by 60%",
      "Automated PCI-DSS compliance reporting"
    ],
    "anticipated_objections": [
      {"objection": "existing_vendor", "counter": "integration_story"},
      {"objection": "budget_freeze", "counter": "roi_calculation"}
    ],
    "cadence": {
      "day_1": {"channel": "linkedin", "action": "connection_request_with_note"},
      "day_3": {"channel": "email", "action": "value_prop_email"},
      "day_7": {"channel": "linkedin", "action": "share_relevant_content"},
      "day_14": {"channel": "email", "action": "case_study_follow_up"}
    },
    "fit_score": 0.82,
    "confidence": 0.75,
    "reasoning": "High fit due to recent Series B + active hiring for compliance roles. CTO is active on LinkedIn (posted 3x this week). Similar companies in fintech responded 2.3x better to LinkedIn-first approach."
  }
}
```

### 4.5 Communication Agent

**Role:** Multi-Channel Message Crafting & Delivery  
**Handles States:** `APPROVED`  
**Outputs To:** `OUTREACH_SENT`

Does NOT use generic templates. For each outreach, the Communication Agent:

1. Loads the **approach plan** from the Strategy Agent
2. Loads **episodic memory** (any prior interactions?)
3. Loads the **company profile** and **stakeholder map**
4. Generates a **hyper-personalised message** grounded in real facts about the company
5. Delivers via the appropriate channel (Email, WhatsApp, LinkedIn, Telegram, Call, Instagram)

**Key constraint:** Every claim in the message must trace back to an Evidence record. The agent cannot hallucinate company facts.

### 4.6 Sentiment Agent

**Role:** Response Analysis & Signal Detection  
**Handles States:** `OUTREACH_SENT`, `FOLLOW_UP`  
**Outputs To:** Updates episodic memory; may trigger re-strategy

When a response comes in (email reply, LinkedIn message, WhatsApp response), the Sentiment Agent:

1. **Classifies intent:** Interested / Not Interested / Need More Info / Objection / Out of Office / Wrong Person
2. **Extracts signals:** Mentioned budget? Asked for demo? Forwarded to someone else?
3. **Scores sentiment:** -1.0 (hostile) to +1.0 (enthusiastic)
4. **Records in episodic memory** for future reference
5. **Updates semantic memory** statistics (was this approach successful?)

### 4.7 Orchestrator Agent (Meta-Agent)

**Role:** Pipeline Coordination, Industry-Adaptive Routing, Conflict Resolution  
**Handles States:** All (meta-level)

The Orchestrator is not just a dispatcher — it is the system's **planning agent**. It:

1. **Selects the IKP** based on the lead's industry classification
2. **Routes leads** to the correct agent based on current state + IKP configuration
3. **Resolves conflicts** when agents disagree (e.g., Intelligence Agent found two possible websites)
4. **Manages cadence timing** — doesn't send all follow-ups at once
5. **Handles errors** — retries with backoff, escalates to human on repeated failures
6. **Learns pipeline efficiency** — tracks which agent sequences produce the best outcomes

---

## 5. Industry Knowledge Packs (IKPs)

An IKP is a **declarative configuration** that tells every agent how to behave for a specific industry. No code changes needed — drop in a new IKP and the system adapts.

### 5.1 IKP Structure

```json
{
  "ikp_id": "finance_banking",
  "display_name": "Finance — Banking & Financial Services",
  "version": "1.0",
  
  "industry_context": {
    "description": "Banking, insurance, fintech, and financial services companies",
    "regulatory_bodies": ["RBI", "SEBI", "IRDAI"],
    "compliance_frameworks": ["PCI-DSS", "SOC 2", "ISO 27001"],
    "sales_cycle": {
      "typical_length_days": 90,
      "complexity": "HIGH",
      "stages": ["Discovery", "Technical Evaluation", "Security Review", "Procurement", "Legal"]
    }
  },
  
  "buyer_personas": [
    {
      "role": "CTO / CIO",
      "seniority": "C-Suite",
      "priorities": ["digital_transformation", "security", "scalability"],
      "messaging_tone": "technical_consultative",
      "preferred_channels": ["linkedin", "email"],
      "typical_objections": ["security_concerns", "legacy_integration", "vendor_lock_in"]
    },
    {
      "role": "CISO / VP Security",
      "seniority": "VP",
      "priorities": ["compliance", "threat_detection", "audit_readiness"],
      "messaging_tone": "security_focused_formal",
      "preferred_channels": ["email", "conference"],
      "typical_objections": ["certification_requirements", "data_residency", "penetration_test_results"]
    }
  ],
  
  "qualification_criteria": {
    "minimum_signals": 3,
    "required_signals": ["has_budget_indicators", "has_decision_maker_identified"],
    "disqualification_signals": ["competitor_customer", "too_small_revenue", "recent_vendor_switch"],
    "scoring_weights": {
      "company_size": 0.15,
      "growth_signals": 0.20,
      "pain_point_match": 0.30,
      "budget_indicators": 0.20,
      "relationship_access": 0.15
    }
  },
  
  "outreach_rules": {
    "max_touchpoints_before_pause": 7,
    "minimum_gap_between_touches_hours": 48,
    "channels_allowed": ["email", "linkedin", "call"],
    "channels_blocked": ["whatsapp", "instagram"],
    "requires_approval_for": ["first_outreach", "pricing_discussion"],
    "compliance_disclaimers": ["This communication is for business purposes only."],
    "blackout_periods": ["quarter_end_week", "audit_season"]
  },
  
  "intelligence_sources": {
    "primary": ["company_website", "linkedin", "rbi_registry"],
    "secondary": ["crunchbase", "news", "job_postings"],
    "skip": ["google_maps"]
  },
  
  "messaging_templates": {
    "initial_outreach": {
      "angle": "compliance_automation",
      "structure": ["personalised_hook", "pain_point_reference", "value_proposition", "social_proof", "soft_cta"],
      "max_length_words": 150,
      "formality": "HIGH"
    }
  }
}
```

### 5.2 Supported IKPs (Phase 1)

| IKP | Key Differences |
|---|---|
| **Finance (Banking/Fintech)** | Long sales cycle, compliance-heavy, LinkedIn + email only, security objections dominant |
| **IT / SaaS** | Medium cycle, technical buyers, LinkedIn-first, demo-driven, freemium/trial common |
| **B2B Manufacturing** | Relationship-heavy, phone + email, long procurement cycles, RFP/RFQ process |
| **Supply Chain / Logistics** | Operational buyers, ROI-focused, WhatsApp acceptable in India, volume/pricing discussions |

### 5.3 IKP Loading

```python
# The Orchestrator loads the IKP at pipeline start
ikp = IKPRegistry.load("finance_banking")

# Every agent receives the IKP through AgentContext
ctx.extra["ikp"] = ikp

# Agents use IKP to configure behaviour
channels = ikp["outreach_rules"]["channels_allowed"]
personas = ikp["buyer_personas"]
scoring_weights = ikp["qualification_criteria"]["scoring_weights"]
```

---

## 6. Orchestrator Design

### 6.1 Adaptive Routing

The Orchestrator doesn't follow a fixed pipeline order. It uses the IKP + lead state + memory to decide **what to do next**:

```python
class OrchestratorAgent:
    """
    Meta-agent that decides which specialist agent runs next.
    
    Unlike a static pipeline, the Orchestrator can:
    - Skip stages (if data is already available)
    - Repeat stages (if results were low-confidence)
    - Reorder stages (if the IKP prioritises certain steps)
    - Fork parallel work (e.g., Intelligence + Relationship Mapping simultaneously)
    """
    
    async def decide_next_action(self, lead_id: int) -> AgentAction:
        lead = self.load_lead(lead_id)
        ikp = self.load_ikp(lead.industry)
        history = await self.memory.recall_episodic(lead_id)
        
        # Decision tree informed by IKP
        if lead.state == "NEW":
            return AgentAction(agent="intelligence", priority="HIGH")
        
        if lead.state == "INTELLIGENCE_GATHERED":
            if ikp.requires_deep_profiling:
                return AgentAction(agent="profiler", priority="HIGH")
            else:
                return AgentAction(agent="strategy", priority="MEDIUM")  # Skip profiling
        
        if lead.state == "OUTREACH_SENT":
            days_since = (now() - lead.last_outreach).days
            if days_since >= ikp.minimum_gap_between_touches:
                if len(history.failed_attempts) >= ikp.max_touchpoints_before_pause:
                    return AgentAction(agent="orchestrator", action="PAUSE_LEAD")
                return AgentAction(agent="communication", priority="MEDIUM")
            else:
                return AgentAction(agent=None, action="WAIT")  # Too soon
```

### 6.2 Conflict Resolution

When agents produce conflicting data:

1. **Confidence-based:** Higher confidence wins
2. **Recency-based:** More recent data wins (tie-breaker)
3. **Source-hierarchy:** Official website > LinkedIn > News > Directory
4. **LLM arbitration:** When automated rules can't resolve, the Orchestrator asks the LLM to reason about which is correct

---

## 7. Lead Lifecycle State Machine

Expanded from the basic pipeline to reflect the full cognitive workflow:

```
  ┌─────┐
  │ NEW │
  └──┬──┘
     │
     ▼
  ┌──────────────────────┐
  │ INTELLIGENCE_GATHERED │  ← Intelligence Agent (multi-source fusion)
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────┐
  │   PROFILED    │  ← Profiler Agent (deep company analysis)
  └──────┬───────┘
         │
         ▼
  ┌──────────────────────┐
  │ RELATIONSHIPS_MAPPED  │  ← Relationship Mapper (org chart + stakeholders)
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────┐
  │   STRATEGY_SET    │  ← Strategy Agent (approach plan + cadence)
  └────────┬─────────┘
           │
           ▼
  ┌────────────────────┐
  │ APPROVAL_PENDING    │  ← Human-in-the-loop gate
  └───┬────────┬───────┘
      │        │
  APPROVED  REJECTED ──► DORMANT / NEW (retry)
      │
      ▼
  ┌────────────────┐
  │ OUTREACH_SENT   │  ← Communication Agent
  └───────┬────────┘
          │
          ▼
  ┌─────────────┐
  │  FOLLOW_UP   │  ← Sentiment Agent + Communication Agent
  └──┬──┬──┬────┘
     │  │  │
    WON │ DORMANT
       LOST

  Any state ──► FAILED (error) ──► NEW (retry)
  Any state ──► PAUSED (manual hold) ──► Any (resume)
```

### State Additions vs. Original

| New State | Rationale |
|---|---|
| `INTELLIGENCE_GATHERED` | Separates data collection from analysis — the Intelligence Agent collects raw data, the Profiler Agent analyses it |
| `PROFILED` | Company profile is a first-class stage, not a side-effect of enrichment |
| `RELATIONSHIPS_MAPPED` | Decision-maker identification is critical enough to be its own stage |

Implementation: [`app/core/state_machine.py`](app/core/state_machine.py) — update `LeadState` enum and `_TRANSITIONS` map.

---

## 8. Agent Communication Protocol

Agents communicate through the **Blackboard pattern** — a shared, observable state space where agents post findings and other agents consume them.

### 8.1 Blackboard Messages

```python
@dataclass
class BlackboardMessage:
    id: str                          # UUID
    source_agent: str                # "intelligence_agent"
    target_agent: Optional[str]      # None = broadcast to all
    message_type: str                # FINDING | REQUEST | CONFLICT | DECISION
    lead_id: int
    
    payload: Dict[str, Any]          # agent-specific data
    priority: str                    # LOW | MEDIUM | HIGH | CRITICAL
    
    created_at: datetime
    consumed_by: List[str]           # which agents have read this
```

### 8.2 Message Types

| Type | Example | Usage |
|---|---|---|
| `FINDING` | "Intelligence Agent found 3 LinkedIn profiles for this company" | One agent shares data for others to use |
| `REQUEST` | "Strategy Agent requests Profiler to extract tech stack info" | One agent asks another for specific work |
| `CONFLICT` | "Website says 50 employees, LinkedIn says 200" | Agent flags inconsistency for Orchestrator |
| `DECISION` | "Orchestrator resolved: use LinkedIn count (higher confidence)" | Orchestrator broadcasts a resolution |

### 8.3 Event Log (Audit Trail)

Every agent action is logged for reproducibility and debugging:

```python
class AgentEventLog(Base):
    __tablename__ = "agent_event_log"
    
    id: int
    lead_id: int
    agent_name: str
    event_type: str              # STARTED | COMPLETED | FAILED | SKIPPED | APPROVAL_REQUESTED
    
    input_summary: str           # hashed/truncated context
    output_summary: str          # hashed/truncated result
    
    state_before: str
    state_after: str
    
    duration_ms: float
    llm_calls_made: int
    tokens_used: int
    
    created_at: datetime
```

---

## 9. LLM Gateway & Reasoning Layer

### 9.1 Gateway Design

All LLM calls go through `LLMGateway` — agents never import provider SDKs directly.

```
┌─────────────────────────────────────────────────────────┐
│                     LLM Gateway                          │
│                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │   Groq   │───►│  Gemini  │───►│   Mock   │           │
│  │ (primary)│    │(fallback)│    │(testing) │           │
│  └──────────┘    └──────────┘    └──────────┘           │
│                                                          │
│  ┌─────────────────────────────────────────────┐        │
│  │            Prompt Registry                    │        │
│  │                                               │        │
│  │  PROFILER_SYSTEM_PROMPT                       │        │
│  │  STRATEGY_SYSTEM_PROMPT                       │        │
│  │  COMMUNICATION_SYSTEM_PROMPT                  │        │
│  │  SENTIMENT_ANALYSIS_PROMPT                    │        │
│  │  CONFLICT_RESOLUTION_PROMPT                   │        │
│  └─────────────────────────────────────────────┘        │
│                                                          │
│  ┌─────────────────────────────────────────────┐        │
│  │            Guardrails                         │        │
│  │                                               │        │
│  │  • Token budget per agent per call            │        │
│  │  • JSON schema validation on output           │        │
│  │  • Hallucination detection (cross-ref facts)  │        │
│  │  • Retry with reformulated prompt on failure  │        │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### 9.2 Prompt Registry

Prompts are **versioned, templated, and separated from agent code**:

```python
PROMPT_REGISTRY = {
    "profiler_analysis_v2": {
        "system": """You are a senior business analyst. Analyze the company data and produce a structured profile.
GUARDRAILS:
- Only state facts supported by the provided evidence
- Mark inferences with confidence levels
- Output valid JSON matching the CompanyProfile schema""",
        
        "user_template": """Company: {company_name}
Industry: {industry}
Evidence collected: {evidence_summary}
Industry context: {ikp_context}

Produce a CompanyProfile JSON.""",
        
        "output_schema": "CompanyProfile",
        "max_tokens": 2000,
        "temperature": 0.3,
    }
}
```

### 9.3 Hallucination Prevention

Every LLM-generated fact is **cross-referenced against the Evidence table**:

1. LLM generates: "Company has 500 employees"
2. System checks: Is there an Evidence record supporting "employee_count = 500"?
3. If YES → fact is accepted with the evidence's confidence score
4. If NO → fact is flagged as `unverified` and not used for decision-making

---

## 10. Data Model

### 10.1 New Tables (additions to existing schema)

```sql
-- Episodic Memory: interaction history per lead
CREATE TABLE episodic_memory (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    agent_name VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,        -- OUTREACH_SENT, RESPONSE_RECEIVED, etc.
    channel VARCHAR,
    content_summary TEXT,
    raw_content TEXT,
    outcome VARCHAR,                     -- POSITIVE, NEGATIVE, NEUTRAL, NO_RESPONSE
    sentiment_score REAL,
    key_signals JSON,
    lessons_learned TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Semantic Memory: domain knowledge
CREATE TABLE semantic_memory (
    id INTEGER PRIMARY KEY,
    category VARCHAR NOT NULL,           -- BUYER_PERSONA, CHANNEL_PERFORMANCE, etc.
    industry VARCHAR NOT NULL,
    knowledge_key VARCHAR NOT NULL,
    knowledge_value JSON NOT NULL,
    source VARCHAR DEFAULT 'ikp_default',
    confidence REAL DEFAULT 1.0,
    times_applied INTEGER DEFAULT 0,
    times_successful INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- Agent Event Log: full audit trail
CREATE TABLE agent_event_log (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    agent_name VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    state_before VARCHAR,
    state_after VARCHAR,
    duration_ms REAL,
    llm_calls_made INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Blackboard: inter-agent messages
CREATE TABLE blackboard_messages (
    id VARCHAR PRIMARY KEY,
    source_agent VARCHAR NOT NULL,
    target_agent VARCHAR,
    message_type VARCHAR NOT NULL,
    lead_id INTEGER REFERENCES leads(id),
    payload JSON,
    priority VARCHAR DEFAULT 'MEDIUM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    consumed_by JSON DEFAULT '[]'
);

-- Stakeholder Map: decision-makers per lead
CREATE TABLE stakeholder_map (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    person_name VARCHAR NOT NULL,
    role VARCHAR,
    seniority VARCHAR,
    linkedin_url VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    is_decision_maker BOOLEAN DEFAULT FALSE,
    is_champion BOOLEAN DEFAULT FALSE,
    contact_priority INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Industry Knowledge Packs: configuration store
CREATE TABLE industry_knowledge_packs (
    id INTEGER PRIMARY KEY,
    ikp_id VARCHAR UNIQUE NOT NULL,
    display_name VARCHAR NOT NULL,
    version VARCHAR DEFAULT '1.0',
    config JSON NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 10.2 Full ERD

```
┌──────────┐     ┌──────────────┐     ┌────────────────────┐
│  leads   │◄───►│  evidence    │     │  company_profiles  │
│          │◄───►│              │     │                    │
│          │◄───►│              │     │                    │
└────┬─────┘     └──────────────┘     └────────────────────┘
     │
     ├──────────►┌──────────────────┐
     │           │ episodic_memory  │    ← NEW: interaction history
     │           └──────────────────┘
     │
     ├──────────►┌──────────────────┐
     │           │ stakeholder_map  │    ← NEW: decision-makers
     │           └──────────────────┘
     │
     ├──────────►┌──────────────────┐
     │           │ strategic_fits   │
     │           └──────────────────┘
     │
     ├──────────►┌──────────────────┐
     │           │ approval_queue   │
     │           └──────────────────┘
     │
     ├──────────►┌──────────────────┐
     │           │buyer_intelligence│
     │           └──────────────────┘
     │
     └──────────►┌──────────────────┐
                 │ agent_event_log  │    ← NEW: audit trail
                 └──────────────────┘

     ┌──────────────────────┐
     │   semantic_memory    │    ← NEW: domain knowledge (global, not per-lead)
     └──────────────────────┘

     ┌──────────────────────┐
     │  blackboard_messages │    ← NEW: inter-agent communication
     └──────────────────────┘

     ┌──────────────────────┐
     │ industry_knowledge_  │    ← NEW: IKP configuration store
     │ packs                │
     └──────────────────────┘

     ┌──────────────────────┐
     │ salesperson_settings │    (existing)
     └──────────────────────┘

     ┌──────────────────────┐
     │ industry_playbooks   │    (existing, will be merged into IKP)
     └──────────────────────┘
```

---

## 11. API Design

### 11.1 Pipeline Endpoints (New)

```
POST   /api/pipeline/{lead_id}/advance          # Advance one step
POST   /api/pipeline/{lead_id}/run-full          # Run through full pipeline
GET    /api/pipeline/{lead_id}/history           # Audit trail
POST   /api/pipeline/batch                       # Batch-process multiple leads
GET    /api/pipeline/{lead_id}/memory/episodic   # View interaction history
GET    /api/pipeline/{lead_id}/stakeholders      # View stakeholder map
```

### 11.2 IKP Management Endpoints (New)

```
GET    /api/ikp                                  # List available IKPs
GET    /api/ikp/{ikp_id}                         # Get IKP configuration
POST   /api/ikp                                  # Create/upload new IKP
PUT    /api/ikp/{ikp_id}                         # Update IKP
```

### 11.3 Memory Endpoints (New)

```
GET    /api/memory/semantic?industry=finance      # Query semantic memory
GET    /api/memory/semantic/performance           # Channel performance stats
POST   /api/memory/semantic                       # Add knowledge manually
```

### 11.4 Existing Endpoints (Preserved)

All existing endpoints continue to work unchanged. The new architecture wraps around them — the `/api/leads/generate` endpoint still calls the LeadGenerationAgent, which now internally uses the Intelligence Agent.

---

## 12. Security & Compliance

| Area | Architecture Decision |
|---|---|
| **Credential Storage** | All channel credentials (SMTP, Twilio, Instagram) encrypted at rest using Fernet symmetric encryption. Decrypted only in-memory at call time. |
| **API Authentication** | JWT tokens with role-based access (admin, salesperson, viewer). API keys for programmatic access. |
| **Data Provenance** | Every data point traces to a source URL, extraction method, and confidence score. Full audit trail in `agent_event_log`. |
| **LLM Data Leakage** | Sensitive fields (revenue, contact info) are masked before being sent to external LLM APIs. Only the LLM Gateway handles masking/unmasking. |
| **Rate Limiting** | Per-IP and per-user rate limits on all endpoints. Per-lead outreach limits enforced by IKP `outreach_rules`. |
| **GDPR/Privacy** | Leads can be fully deleted (cascade to all related tables). No data retention after deletion. Consent tracking for outreach. |
| **Industry Compliance** | IKPs define compliance disclaimers, blackout periods, and channel restrictions per industry. |

---

## 13. Evaluation Framework

For the research paper, we need quantitative metrics:

### 13.1 Agent-Level Metrics

| Metric | How Measured |
|---|---|
| **Intelligence Recall** | % of verifiable facts about a company that the Intelligence Agent discovers |
| **Profiler Accuracy** | Expert rating of company profile quality (1–5 scale, blind evaluation) |
| **Relationship Mapper Precision** | % of identified decision-makers that are actually decision-makers |
| **Strategy Agent Conversion Lift** | A/B test: Strategy Agent recommendations vs. random approach |
| **Communication Agent Personalisation Score** | LLM-judge rating of message personalisation (1–10) |
| **Sentiment Agent F1** | Precision/Recall on intent classification vs. human labels |

### 13.2 System-Level Metrics

| Metric | Target |
|---|---|
| **Lead-to-Meeting Conversion Rate** | Baseline → 2x improvement |
| **Response Rate (cold outreach)** | Industry avg ~3% → target 8-12% |
| **Pipeline Velocity** | Time from NEW → OUTREACH_SENT |
| **Memory Utilisation** | % of decisions where episodic/semantic memory was consulted |
| **Cross-Industry Adaptability** | IKP switch should require 0 code changes |
| **Agent Collaboration Efficiency** | % of blackboard messages that influenced downstream agent decisions |

### 13.3 Ablation Studies (for the paper)

1. **With vs. without episodic memory** — Does remembering past interactions improve response rates?
2. **With vs. without semantic memory** — Does industry knowledge improve scoring accuracy?
3. **With vs. without Relationship Mapper** — Does identifying the right person matter?
4. **Static pipeline vs. adaptive Orchestrator** — Does dynamic routing outperform fixed ordering?
5. **Single LLM vs. fallback chain** — How does reliability compare?

---

## 14. Implementation Roadmap

### Phase A — Core Architecture (Shubham — Current)
- [x] `BaseAgent` contract + `AgentContext` + `AgentResult`
- [x] `LeadStateMachine` with guarded transitions
- [x] `LLMGateway` with fallback chain (Groq → Gemini → Mock)
- [x] `SalesPipeline` orchestrator (advance / run_full)
- [x] 17 core architecture tests passing
- [ ] Memory layer: `WorkingMemory`, `EpisodicMemory`, `SemanticMemory` models
- [ ] Blackboard message bus
- [ ] Agent event log
- [ ] IKP registry + loader + 4 default IKPs
- [ ] Migrate `WebDiscoveryAgent` → `IntelligenceAgent` (BaseAgent interface)
- [ ] Migrate `ResearchOrchestrator` → `ProfilerAgent` (BaseAgent interface)
- [ ] Build `RelationshipMapperAgent`
- [ ] Build `StrategyAgent` (replaces MatchingEngine + IndustryAgent)
- [ ] Pipeline API endpoints (`/api/pipeline/*`)

### Phase B — Communication & Sentiment (Lavanya)
- [ ] Migrate `OutreachAgent` → `CommunicationAgent` (BaseAgent interface)
- [ ] Build `SentimentAgent` (response analysis + intent classification)
- [ ] Follow-up cadence engine (Day 1, 3, 7, 14 scheduling)
- [ ] Email open/click tracking integration
- [ ] Conversation thread management per channel
- [ ] Episodic memory recording for all outreach events

### Phase C — Orchestrator Intelligence (Akshat)
- [ ] Build `OrchestratorAgent` (adaptive routing, not static pipeline)
- [ ] Implement conflict resolution logic
- [ ] Lead scoring v2 using semantic memory + multi-signal model
- [ ] IKP-driven pipeline reconfiguration
- [ ] Batch processing with concurrency controls
- [ ] Database migration to PostgreSQL + connection pooling

### Phase D — Learning & Optimisation
- [ ] Semantic memory auto-update from outcome data
- [ ] A/B testing framework for messaging strategies
- [ ] Confidence decay for stale knowledge
- [ ] Pipeline efficiency analytics dashboard

### Phase E — Production Hardening
- [ ] JWT authentication + RBAC
- [ ] Credential encryption (Fernet)
- [ ] WebSocket real-time pipeline updates
- [ ] Background task queue (Celery / ARQ)
- [ ] Docker + docker-compose
- [ ] CI/CD (GitHub Actions)
- [ ] Monitoring (Sentry + Prometheus)

---

## 15. Team Integration Contracts

### For Lavanya — Communication & Sentiment Agents

Your agents implement `BaseAgent`. Here's the exact contract:

```python
from app.core.base_agent import BaseAgent, AgentContext, AgentResult, AgentStatus
from app.core.state_machine import LeadState

class CommunicationAgent(BaseAgent):
    name = "communication_agent"
    handles_states = {LeadState.APPROVED}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        ikp = ctx.extra.get("ikp", {})
        
        # 1. RECALL episodic memory for this lead
        past_interactions = query_episodic_memory(ctx.db_session, ctx.lead_id)
        
        # 2. Load approach plan from strategic_fit
        approach = load_strategic_fit(ctx.db_session, ctx.lead_id)
        
        # 3. Generate personalised message via LLM Gateway
        gateway = LLMGateway.default()
        message = await gateway.generate_text(
            prompt=build_outreach_prompt(ctx, approach, past_interactions, ikp),
            system_prompt=COMMUNICATION_SYSTEM_PROMPT
        )
        
        # 4. Send via appropriate channel
        channel = approach["opening_channel"]
        result = await send_message(channel, message, ctx)
        
        # 5. RECORD in episodic memory
        record_episodic_memory(ctx.db_session, ctx.lead_id, "OUTREACH_SENT", ...)
        
        return AgentResult(
            status=AgentStatus.SUCCESS,
            next_state=LeadState.OUTREACH_SENT,
            message=f"Sent {channel} message to {ctx.lead_data['company_name']}"
        )


class SentimentAgent(BaseAgent):
    name = "sentiment_agent"
    handles_states = {LeadState.OUTREACH_SENT, LeadState.FOLLOW_UP}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        # Analyse response, classify intent, update episodic memory
        ...
```

### For Akshat — Orchestrator & Scoring

```python
class OrchestratorAgent(BaseAgent):
    name = "orchestrator"
    handles_states = set(LeadState)  # handles all states (meta-level)

    async def execute(self, ctx: AgentContext) -> AgentResult:
        ikp = IKPRegistry.load_for_industry(ctx.lead_data["industry"])
        
        # Adaptive routing: decide which agent should run next
        next_agent = self.decide_next_agent(ctx, ikp)
        
        # Delegate to the chosen agent
        result = await next_agent.run(ctx)
        
        # Record decision in event log
        log_agent_event(ctx.db_session, ctx.lead_id, self.name, "ROUTED", ...)
        
        return result


class LeadScoringAgentV2(BaseAgent):
    name = "lead_scoring_v2"
    handles_states = {LeadState.RELATIONSHIPS_MAPPED}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        ikp = ctx.extra.get("ikp", {})
        weights = ikp["qualification_criteria"]["scoring_weights"]
        
        # Multi-signal scoring using semantic memory
        signals = extract_scoring_signals(ctx)
        score = weighted_score(signals, weights)
        
        return AgentResult(
            status=AgentStatus.SUCCESS,
            next_state=LeadState.SCORED,
            artifacts={"score": score, "signals": signals}
        )
```

### Key Rules for Everyone

1. **Never import LLM providers directly.** Always use `LLMGateway.default()`.
2. **Never commit to the DB inside an agent.** Return an `AgentResult`; the pipeline commits.
3. **Always record episodic memory** after any interaction with a lead.
4. **Always load the IKP** from `ctx.extra["ikp"]` — never hardcode industry logic.
5. **Every data point needs an Evidence record** with source URL and confidence score.

---

## References

1. Atkinson, R.C. & Shiffrin, R.M. (1968). Human Memory: A Proposed System and Its Control Processes.
2. Tulving, E. (1972). Episodic and Semantic Memory. Organisation of Memory.
3. Erman, L.D. et al. (1980). The Hearsay-II Speech Understanding System: Integrating Knowledge to Resolve Uncertainty. *Computing Surveys*. (Blackboard architecture)
4. Wooldridge, M. & Jennings, N.R. (1995). Intelligent Agents: Theory and Practice. *Knowledge Engineering Review*.
5. Park, J.S. et al. (2023). Generative Agents: Interactive Simulacra of Human Behavior. *UIST 2023*. (Memory architecture for LLM agents)

---

*MASAA — Multi-Agent Sales Automation Architecture*  
*Dynamic CRM Sales Agents Orchestration Project*  
*[GitHub](https://github.com/Shubham231005/Dynamic_CRM_Sales_Agents_Orchestration)*
