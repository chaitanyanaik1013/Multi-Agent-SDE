from langgraph.graph import StateGraph, END
from multi_agent_sde.state import WorkflowState
from multi_agent_sde.agents.pm_agent import run_pm_agent
from multi_agent_sde.agents.architect_agent import run_architect_agent
from multi_agent_sde.agents.backend_agent import run_backend_agent
from multi_agent_sde.agents.qa_agent import run_qa_agent
from langgraph.checkpoint.memory import MemorySaver

builder = StateGraph(WorkflowState)

builder.add_node("pm_agent", run_pm_agent)
builder.add_node("architect_agent", run_architect_agent)
builder.add_node("backend_agent", run_backend_agent)
builder.add_node("qa_agent", run_qa_agent)

builder.set_entry_point("pm_agent")
builder.add_edge("pm_agent", "architect_agent")
builder.add_edge("architect_agent", "backend_agent")
builder.add_edge("backend_agent", "qa_agent")
builder.add_edge("qa_agent", END)

state = {"project_id":"test-1", "user_input":"Build a subscription tracking app."}
memory = MemorySaver()
workflow = builder.compile(checkpointer=memory, interrupt_before=["architect_agent"])
config = {"configurable": {"thread_id": "project-test-1"}}
result = workflow.invoke(state, config)
print(result)

