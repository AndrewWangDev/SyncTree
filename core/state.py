from dataclasses import dataclass, field

@dataclass
class GitState:
    isRepo: bool = False
    hasModified: bool = False
    hasStaged: bool = False
    commitsAhead: int = 0
    currentBranch: str = ""
    commitHistory: list = field(default_factory=list)
    fileStatuses: dict = field(default_factory=dict)
    
