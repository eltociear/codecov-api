import enum


class RepositoryOrdering(enum.Enum):
    COMMIT_DATE = "latest_commit_at"
    COVERAGE = "coverage"
    ID = "repoid"
    NAME = "name"


class OrderingDirection(enum.Enum):
    ASC = "ascending"
    DESC = "descending"


class CoverageLine(enum.Enum):
    H = "hit"
    M = "miss"
    P = "partial"

class ComparisonError(enum.Enum):
    MISSING_BASE_REPORT = "missing_base_report"
    MISSING_HEAD_REPORT = "missing_head_report"
