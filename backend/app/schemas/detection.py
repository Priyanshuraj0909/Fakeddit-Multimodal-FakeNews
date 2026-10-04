"""News input and evidence report contracts."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Verdict = Literal['supported', 'contradicted', 'mixed', 'insufficient_evidence']


class DetectionInput(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    source_url: str = Field(default='', max_length=2000)
    publication_date: str = Field(default='', max_length=10)


class ClaimAssessment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    statement: str = Field(min_length=1, max_length=1200)
    verdict: Verdict
    explanation: str = Field(min_length=1, max_length=2500)
    evidence_ids: list[int] = Field(max_length=8)


class EvidenceAssessment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    summary: str = Field(min_length=1, max_length=2500)
    claims: list[ClaimAssessment] = Field(min_length=1, max_length=5)


# Groq's strict output schema has required fields and no additional properties.
EVIDENCE_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'summary': {'type': 'string'},
        'claims': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'properties': {
                'statement': {'type': 'string'},
                'verdict': {'type': 'string', 'enum': ['supported', 'contradicted', 'mixed', 'insufficient_evidence']},
                'explanation': {'type': 'string'},
                'evidence_ids': {'type': 'array', 'items': {'type': 'integer'}},
            },
            'required': ['statement', 'verdict', 'explanation', 'evidence_ids'],
        }},
    },
    'required': ['summary', 'claims'],
}
