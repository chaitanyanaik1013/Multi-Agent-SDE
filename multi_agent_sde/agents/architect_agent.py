import time
from multi_agent_sde.shared_client import client

def run_architect_agent(state: dict) -> dict:
    system_prompt = "You are a senior software architect. Given a set of requirements, design a system architecture: pick a tech stack with brief justifications, describe the high-level components/layers, and define a database schema (tables and key fields). Return it as a structured markdown document."
    user_prompt = f"Requirements:\n{state['requirements']}"
    start = time.time()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        system=system_prompt,
        messages=[
            {"role":"user", "content":user_prompt}
        ]
    )
    architecture = response.content[0].text
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    cost_usd = (tokens_in/1_000_000)*1.00 + (tokens_out/1_000_000)*5.00
    latency = time.time()-start
    return {
        **state,
        "architecture": architecture,
        "metrics": {
            **state.get("metrics", {}),
            "architect_agent": {
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": cost_usd,
                "latency": latency,
            }
        }
    }