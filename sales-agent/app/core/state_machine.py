"""
Lead State Machine
====================
Defines the legal states a lead can be in and which transitions are allowed.
The Pipeline Orchestrator uses this to enforce ordering guarantees.

The MASAA cognitive pipeline adds two new intermediate states compared to a
basic CRUD pipeline:

  - INTELLIGENCE_GATHERED — raw multi-source data collected (Intelligence Agent)
  - PROFILED              — deep company analysis complete  (Profiler Agent)
  - RELATIONSHIPS_MAPPED  — decision-makers identified      (Relationship Mapper)

State Diagram
─────────────

  NEW ──► INTELLIGENCE_GATHERED ──► PROFILED ──► RELATIONSHIPS_MAPPED
                                                        │
                                                        ▼
                                                     SCORED
                                                        │
                                                        ▼
                                                  STRATEGY_SET
                                                        │
                                                        ▼
                                               APPROVAL_PENDING
                                                 │           │
                                           APPROVED      REJECTED
                                                 │
                                                 ▼
                                           OUTREACH_SENT
                                                 │
                                                 ▼
                                             FOLLOW_UP
                                            /    |    \\
                                         WON   LOST  DORMANT

  Any state ──► FAILED   (on unrecoverable error)
  Any state ──► PAUSED   (manual hold)
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet


class LeadState(str, Enum):
    """Every possible state a lead can occupy in the MASAA sales pipeline."""

    # ── Acquisition & Intelligence ──
    NEW                     = "NEW"
    INTELLIGENCE_GATHERED   = "INTELLIGENCE_GATHERED"  # multi-source data fusion complete
    PROFILED                = "PROFILED"                # deep company analysis complete
    RELATIONSHIPS_MAPPED    = "RELATIONSHIPS_MAPPED"    # decision-makers identified

    # ── Legacy aliases (kept for backward compat with existing DB rows) ──
    DISCOVERED              = "DISCOVERED"
    RESEARCHED              = "RESEARCHED"

    # ── Qualification ──
    SCORED                  = "SCORED"
    STRATEGY_SET            = "STRATEGY_SET"

    # ── Human Gate ──
    APPROVAL_PENDING        = "APPROVAL_PENDING"
    APPROVED                = "APPROVED"
    REJECTED                = "REJECTED"

    # ── Outreach ──
    OUTREACH_SENT           = "OUTREACH_SENT"
    FOLLOW_UP               = "FOLLOW_UP"

    # ── Terminal ──
    WON                     = "WON"
    LOST                    = "LOST"
    DORMANT                 = "DORMANT"

    # ── Meta ──
    FAILED                  = "FAILED"
    PAUSED                  = "PAUSED"


# ---------------------------------------------------------------------------
# Allowed transitions
#
# Design rule: Skip-transitions are allowed so that pre-enriched imports can
# jump past stages they don't need.  The IKP controls which skips are
# actually used — the state machine only prevents impossible orderings.
# ---------------------------------------------------------------------------

_FAIL_PAUSE = frozenset({LeadState.FAILED, LeadState.PAUSED})

_TRANSITIONS: Dict[LeadState, FrozenSet[LeadState]] = {
    # Acquisition flow (new cognitive stages)
    LeadState.NEW: frozenset({
        LeadState.INTELLIGENCE_GATHERED,
        LeadState.DISCOVERED,      # legacy compat
        LeadState.PROFILED,        # skip-allowed
        LeadState.SCORED,          # skip-allowed (pre-scored import)
    }) | _FAIL_PAUSE,

    LeadState.INTELLIGENCE_GATHERED: frozenset({
        LeadState.PROFILED,
        LeadState.RELATIONSHIPS_MAPPED,  # skip-allowed
        LeadState.SCORED,                # skip-allowed
    }) | _FAIL_PAUSE,

    LeadState.PROFILED: frozenset({
        LeadState.RELATIONSHIPS_MAPPED,
        LeadState.SCORED,          # skip-allowed
    }) | _FAIL_PAUSE,

    LeadState.RELATIONSHIPS_MAPPED: frozenset({
        LeadState.SCORED,
    }) | _FAIL_PAUSE,

    # Legacy states map into the new flow
    LeadState.DISCOVERED: frozenset({
        LeadState.RESEARCHED,
        LeadState.PROFILED,
        LeadState.INTELLIGENCE_GATHERED,
        LeadState.SCORED,
    }) | _FAIL_PAUSE,

    LeadState.RESEARCHED: frozenset({
        LeadState.SCORED,
        LeadState.RELATIONSHIPS_MAPPED,
    }) | _FAIL_PAUSE,

    # Qualification
    LeadState.SCORED: frozenset({
        LeadState.STRATEGY_SET,
        LeadState.APPROVAL_PENDING,  # direct gate (combined scoring+strategy)
    }) | _FAIL_PAUSE,

    LeadState.STRATEGY_SET: frozenset({
        LeadState.APPROVAL_PENDING,
        LeadState.OUTREACH_SENT,   # auto-approved (low-risk IKPs)
    }) | _FAIL_PAUSE,

    # Human gate
    LeadState.APPROVAL_PENDING: frozenset({
        LeadState.APPROVED,
        LeadState.REJECTED,
    }) | _FAIL_PAUSE,

    LeadState.APPROVED: frozenset({
        LeadState.OUTREACH_SENT,
    }) | _FAIL_PAUSE,

    LeadState.REJECTED: frozenset({
        LeadState.DORMANT,
        LeadState.NEW,             # retry
    }) | _FAIL_PAUSE,

    # Outreach & follow-up
    LeadState.OUTREACH_SENT: frozenset({
        LeadState.FOLLOW_UP,
    }) | _FAIL_PAUSE,

    LeadState.FOLLOW_UP: frozenset({
        LeadState.WON,
        LeadState.LOST,
        LeadState.DORMANT,
        LeadState.OUTREACH_SENT,   # re-engage
    }) | _FAIL_PAUSE,

    # Terminal states
    LeadState.WON:      frozenset({LeadState.PAUSED}),
    LeadState.LOST:     frozenset({LeadState.PAUSED, LeadState.NEW}),
    LeadState.DORMANT:  frozenset({LeadState.PAUSED, LeadState.NEW}),

    # Meta states
    LeadState.FAILED:   frozenset({LeadState.NEW, LeadState.PAUSED}),
    LeadState.PAUSED:   frozenset(set(LeadState)),  # resume to anywhere
}


class LeadStateMachine:
    """
    Validates and applies state transitions for a lead.

    Usage::

        sm = LeadStateMachine()
        if sm.can_transition(LeadState.NEW, LeadState.INTELLIGENCE_GATHERED):
            new_state = sm.transition(LeadState.NEW, LeadState.INTELLIGENCE_GATHERED)
    """

    @staticmethod
    def can_transition(current: LeadState, target: LeadState) -> bool:
        allowed = _TRANSITIONS.get(current, frozenset())
        return target in allowed

    @staticmethod
    def transition(current: LeadState, target: LeadState) -> LeadState:
        """
        Returns ``target`` if the transition is legal, otherwise raises ValueError.
        """
        if not LeadStateMachine.can_transition(current, target):
            raise ValueError(
                f"Illegal state transition: {current.value} → {target.value}. "
                f"Allowed targets: {[s.value for s in _TRANSITIONS.get(current, frozenset())]}"
            )
        return target

    @staticmethod
    def terminal_states() -> FrozenSet[LeadState]:
        return frozenset({LeadState.WON, LeadState.LOST, LeadState.DORMANT})

    @staticmethod
    def needs_human(state: LeadState) -> bool:
        return state == LeadState.APPROVAL_PENDING
