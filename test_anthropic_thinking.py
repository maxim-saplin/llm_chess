import os
from autogen import ConversableAgent, gather_usage_summary

# Get the Anthropic API key from the environment variable ANTHROPIC_API_KEY_B
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY_B")

messages = [{"role": "user", "content": "Please provide a comparison of JS and TS"}]

llm_config = {
    "config_list": [
        {
            "model": "claude-3-7-sonnet-20250219",
            "api_key": ANTHROPIC_API_KEY,
            "api_type": "anthropic",
        }
    ],
    "temperature": 0.3,
    "top_p": 1.0,
    "timeout": 600,
    "cache_seed": None,
}

agent = ConversableAgent(
    name="test",
    llm_config=llm_config,
)

response = agent.generate_reply(messages=messages)

print(response)

usage = gather_usage_summary([agent])
print(usage)

print("\n\n !!!! THINKING !!!! \n\n")

llm_config = {
    "config_list": [
        {
            "model": "claude-3-7-sonnet-20250219",
            "api_key": ANTHROPIC_API_KEY,
            "api_type": "anthropic",
            "max_tokens": 8192, # override the default value of 4096, max tokens must be greater than thinking budget
            "timeout": 600, # for larger thinking budgets, increase the timeout OR enable streaming
            "thinking": {"type": "enabled", "budget_tokens": 2048},
        }
    ],
    # don't pass in temperature or top_p to avoid exceptions
    # "temperature": 1.0,
    # "top_p": 1.0,
    "cache_seed": None,
}

agent = ConversableAgent(
    name="test",
    llm_config=llm_config,
)

response = agent.generate_reply(
    messages=messages
)

print(response)

usage = gather_usage_summary([agent])
print(usage)
