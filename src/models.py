from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Applicant:
    designation: str | None = None
    name_first: str | None = None
    name_last: str | None = None
    organization: str | None = None
    sequence: int | None = None
    type: str | None = None
    location_id: str | None = None

@dataclass
class Application:
    id: str | None = None
    type: str | None = None
    filing_date: datetime | None = None
    filing_type: str | None = None
    rule_47_flag: bool | None = None
    series_code: str | None = None

@dataclass
class Assignee:
    name: str | None = None
    type: str | None = None
    individual_name_first: str | None = None
    individual_name_last: str | None = None
    organization: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    sequence: int | None = None

@dataclass
class Attorney:
    id: str | None = None
    name_first: str | None = None
    name_last: str | None = None
    organization: str | None = None
    sequence: int | None = None

@dataclass
class Inventor:
    name: str | None = None
    name_first: str | None = None
    name_last: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    sequence: int | None = None

@dataclass
class Figure:
    num_figures: int | None = 0
    num_sheets: int | None = 0

@dataclass
class ForeignPriority:
    filing_date: datetime | None = None
    application_id: str | None = None
    country_filed: str | None = None
    claim_kind: str | None = None
    claim_sequence: int | None = None

@dataclass
class CPC:
    cpc_class: str | None = None
    class_id: str | None = None
    group: str | None = None
    group_id: str | None = None
    section: str | None = None
    sequence: int | None = None
    subclass: str | None = None
    subclass_id: str | None = None
    type: str | None = None

@dataclass
class IPCR:
    action_date: datetime | None = None
    ipc_class: str | None = None
    classification_data_source: str | None = None
    classification_value: str | None = None
    id: str | None = None
    main_group: str | None = None
    section: str | None = None
    sequence: int | None = None
    subclass: str | None = None
    subgroup: str | None = None
    symbol_position: str | None = None

@dataclass
class Examiner:
    art_group: str | None = None
    first_name: str | None = None
    id: str | None = None
    last_name: str | None = None
    role: str | None = None

@dataclass
class Patent:
    id: str
    title: str
    abstract: str | None = None
    date: datetime | None = None
    applicants: list[Applicant] = field(default_factory=list)
    applications: list[Application] = field(default_factory=list)
    assignees: list[Assignee] = field(default_factory=list)
    attorneys: list[Attorney] = field(default_factory=list)
    inventors: list[Inventor] = field(default_factory=list)
    figures: list[Figure] = field(default_factory=list)
    foreign_priorities: list[ForeignPriority] = field(default_factory=list)
    cpc_at_issue: list[CPC] = field(default_factory=list)
    cpc_current: list[CPC] = field(default_factory=list)
    ipcr: list[IPCR] = field(default_factory=list)
    examiners: list[Examiner] = field(default_factory=list)
    type: str | None = None
    year: int | None = None
    earliest_application_date: datetime | None = None
    num_foreign_documents_cited: int | None = None
    num_times_cited_by_us_patents: int | None = None
    num_total_documents_cited: int | None = None
    num_us_applications_cited: int | None = None
    num_us_patents_cited: int | None = None
    processing_days: int | None = None
    term_extension: int | None = None
    uspc_current_mainclass_average_processing_days: int | None = None
    detail_desc_length: int | None = None
    withdrawn: bool | None = None
    wipo_kind: str | None = None
    
    
if __name__ == "__main__":
    p = Patent(
        id="1234567890",
        title="Test Patent",
        abstract="Test Abstract",
        date=datetime.now(),
    )
    print(p)