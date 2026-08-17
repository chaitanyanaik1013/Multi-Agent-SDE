import time
from multi_agent_sde.shared_client import client

def run_backend_agent(state: dict) -> dict:
    system_prompt = "You are a senior backend engineer. Given a system architecture and database schema, produce: a REST API design (endpoints, methods, request/response shapes), SQL migration statements for the schema, an implementation task backlog with effort estimates (S/M/L per task), and notes on authentication and middleware. Return it as a structured markdown document."
    user_prompt = f"Architecture and schema:\n{state['architecture']}"
    start = time.time()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        system=system_prompt,
        messages=[
            {"role":"user", "content":user_prompt}
        ]
    )
    backend_spec = response.content[0].text
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    cost_usd = (tokens_in/1_000_000)*1.00 + (tokens_out/1_000_000)*5.00
    latency = time.time()-start
    return {
        **state,
        "backend_spec": backend_spec,
        "metrics": {
            **state.get("metrics", {}),
            "backend_agent": {
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": cost_usd,
                "latency": latency,
            }
        }
    }