import time
from multi_agent_sde.shared_client import client

def run_pm_agent(state: dict) -> dict:
    system_prompt = "You are a senior product manager. Given a product idea, write a structured requirements document with: functional requirements, user stories, and out-of-scope items."
    user_prompt = f"Product idea: {state['user_input']}"
    start = time.time()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        system=system_prompt,
        messages=[
            {"role":"user", "content":user_prompt}
        ]
    )
    requirements_text = response.content[0].text
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    cost_usd = (tokens_in/1_000_000)*1.00 + (tokens_out/1_000_000)*5.00
    latency = time.time()-start
    return {
        **state,
        "requirements": requirements_text,
        "metrics": {
            **state.get("metrics", {}),
            "pm_agent": {
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": cost_usd,
                "latency": latency,
            }
        }
    }

if __name__=="__main__":
    test_state = {"project_id": "test-1", "user_input": "Build a subscription tracking app"}
    result = run_pm_agent(test_state)
    print(result)
    