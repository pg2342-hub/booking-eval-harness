"""Optional live-model agent: reads the raw transcript and a snapshot of the mock FSM, returns a proposal.

Not run in the included report (no API key in the build environment). To run:
  pip install anthropic pydantic && export ANTHROPIC_API_KEY=...
  python run_eval.py --agent claude --runs 3
Each case runs three times because a model's answers vary between runs.
"""
import json
from typing import List, Literal, Optional

from pydantic import BaseModel

MODEL = "claude-opus-5-5"


class Job(BaseModel):
    job_type: str
    business_unit: str
    fee: Optional[int]
    slot: str
    priority: Literal["Normal", "High", "Urgent"]
    campaign: Optional[str]


class Reschedule(BaseModel):
    job_id: str
    slot: str


class Proposal(BaseModel):
    action: Literal["book", "book_flag", "reschedule", "handoff", "decline"]
    jobs: List[Job]
    reschedule: Optional[Reschedule]
    flags: List[Literal["membership", "job_type", "billing", "promotion", "priority"]]
    offers: List[str]
    handoff_to: Optional[Literal["CSR", "COMM"]]
    safety_instruction: bool
    asked_for_address: bool
    log: List[str]


SYSTEM = """You are a booking agent for a home services company. Decide how to book the request into the
field service system described in the JSON snapshot. Lines in [brackets] are turns you have already taken.
Rules:
- Job check: choose job type and business unit from what the caller describes (the symptom), not only the word they use. Two problems become two jobs.
- Fee check: look up membership by phone, then by service address (street and ZIP). Quote the member service fee only for an active membership at that address. Plan tune-ups are $0. Estimates quote no fee (null).
- Area check: book only into a business unit whose ZIP list includes the service ZIP. A known caller's location on file counts as the address. If there is no address, ask once (set asked_for_address). If no unit covers the ZIP, decline.
- Slot check: use slot ids from the snapshot (each has a day). Book the earliest open routine window the caller accepts; never use an emergency window for routine work. To reschedule, set action "reschedule" with the existing job id and new slot, and leave jobs empty.
- Priority: "Normal" for all routine work, including no-heat calls and same-day requests. This business has not configured any escalation to "High" or "Urgent".
- Campaign: the lead source the caller names (for example "Angi"), exactly as said; otherwise null.
- If a check is unsure and a CSR can fix it before the technician leaves (expired membership, unknown system type, payer is not the occupant, unverified promotion, no same-day capacity for a member), book with action "book_flag" and the matching flag. Offer renewal on an expired membership by putting "renewal" in offers.
- If it cannot be fixed later, do not book: gas smell (tell the caller to leave and call the gas utility or 911, set safety_instruction, hand off to CSR), commercial property (hand off to COMM), billing disputes (hand off to CSR).
Return only the structured proposal."""


class ClaudeAgent:
    name = "claude"

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic()

    def propose(self, case, fsm):
        snapshot = {k: fsm[k] for k in ("fees", "business_units", "equipment", "customers", "slots", "_slots_note")}
        user = (f"FSM snapshot:\n{json.dumps(snapshot)}\n\nCaller phone: {case['facts']['phone']}\n"
                f"Channel: {case['channel']}\nConversation:\n{case['transcript']}")
        try:
            resp = self.client.messages.parse(
                model=MODEL, max_tokens=16000, system=SYSTEM,
                messages=[{"role": "user", "content": user}], output_format=Proposal,
            )
        except Exception as e:  # one API error should fail this case, not the whole run
            return _failed(f"API error: {e}")
        if resp.stop_reason == "refusal" or resp.parsed_output is None:
            return _failed(f"no usable output (stop_reason={resp.stop_reason})")
        return resp.parsed_output.model_dump()


def _failed(reason):
    """A failed call scores as a failure on every case (no action matches "error")."""
    return {"action": "error", "jobs": [], "reschedule": None, "flags": [], "offers": [], "handoff_to": None,
            "safety_instruction": False, "asked_for_address": False, "log": [reason]}
