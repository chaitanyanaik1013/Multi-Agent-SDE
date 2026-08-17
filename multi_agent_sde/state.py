from typing import TypedDict, Optional

class WorkflowState(TypedDict):
    project_id: str
    user_input: str
    requirements: Optional[str]
    architecture: Optional[str]
    backend_spec: Optional[str]
    test_plan: Optional[str]
    metrics: dict
