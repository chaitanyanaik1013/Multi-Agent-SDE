import time
from multi_agent_sde.shared_client import client

def run_qa_agent(state: dict) -> dict:
    system_prompt = "You are a senior QA engineer. Given the requirements, system architecture, and backend implementation spec, produce a test plan: test cases (unit, integration, and end-to-end), an acceptance criteria checklist, key edge cases and failure scenarios, and a testing strategy by layer. Return it as a structured markdown document."
    user_prompt = f"Requirements:\n{state['requirements']}\n\nArchitecture:\n{state['architecture']}\n\nBackend spec:\n{state['backend_spec']}"
    start = time.time()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        system=system_prompt,
        messages=[
            {"role":"user", "content":user_prompt}
        ]
    )
    test_plan = response.content[0].text
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    cost_usd = (tokens_in/1_000_000)*1.00 + (tokens_out/1_000_000)*5.00
    latency = time.time()-start
    return {
        **state,
        "test_plan": test_plan,
        "metrics": {
            **state.get("metrics", {}),
            "qa_agent": {
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": cost_usd,
                "latency": latency,
            }
        }
    }