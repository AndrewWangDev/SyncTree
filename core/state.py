from dataclasses import dataclass, field

@dataclass
class GitState:
    isRepo: bool = False
    hasModified: bool = False
    hasStaged: bool = False
    commitsAhead: int = 0
    currentBranch: str = ""
    branches: list = field(default_factory=list)
    commitHistory: list = field(default_factory=list)
    fileStatuses: dict = field(default_factory=dict)
    canUndo: bool = False
    
