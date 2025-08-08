from autogen import ConversableAgent

from utils import  get_llms


_, llm_config_black = get_llms(black_hyperparams={"reasoning_effort": "high"})

agent = ConversableAgent(
    name="test",
    llm_config=llm_config_black,
    max_consecutive_auto_reply=2,
    human_input_mode="NEVER",
)

response = agent.generate_reply(messages=[{"role": "user", "content": "Hello, how are you?"}])

print(response)
