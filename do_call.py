from autogen import ConversableAgent

from utils import get_llms_autogen, get_llms_autogen_per_model


_, llm_config_black = get_llms_autogen(reasoning_effort="high")
_, llm_config_black2 = get_llms_autogen_per_model(black_config={"reasoning_effort": "high"})

agent = ConversableAgent(
    name="test",
    llm_config=llm_config_black2,
    max_consecutive_auto_reply=2,
    human_input_mode="NEVER",
)

response = agent.generate_reply(messages=[{"role": "user", "content": "Hello, how are you?"}])

print(response)
