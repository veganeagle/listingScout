# models.py

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class PipelineRequest:
    image_url: Optional[str] = None
    listing_url: Optional[str] = None
    listing_source: str = "unknown"
    selected_image_url: Optional[str] = None


@dataclass
class InputPanel:
    submitted_listing_url: Optional[str]
    listing_source: str
    submitted_image_url: Optional[str]
    selected_image_url: Optional[str]
    active_image_url: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)



@dataclass
class MatchRecord:
    url: str
    domain: str
    title: str = ""
    source: str = ""
    match_type: str = "unknown"
    thumbnail_url: Optional[str] = None
    rank: int = 0
    score1: Optional[int] = None
    listing_id: Optional[str] = None
    platform: Optional[str] = None
    hidden_reason: Optional[str] = None
    

@dataclass
class MatchDiscoveryPanel:
    provider: str
    raw_match_count: int
    matches: List[MatchRecord] = field(default_factory=list)


@dataclass
class ClassificationPanel:
    status: str
    direct: List[MatchRecord] = field(default_factory=list)
    ota: List[MatchRecord] = field(default_factory=list)
    unknown: List[MatchRecord] = field(default_factory=list)
    hidden: List[MatchRecord] = field(default_factory=list)

@dataclass
class ContactRecord:
    url: str
    domain: str
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    address: Optional[str] = None
    title: str = ""
    error: Optional[str] = None
    source_bucket: Optional[str] = None
    source_quality: Optional[str] = None
    rank: int = 0
    score1: Optional[int] = None
    

@dataclass
class ContactPanel:
    status: str
    records: List[ContactRecord] = field(default_factory=list)


@dataclass
class PipelineResponse:
    ok: bool
    input_panel: InputPanel
    match_discovery: MatchDiscoveryPanel
    classification: ClassificationPanel
    contact: ContactPanel


@dataclass
class ErrorPayload:
    error: str