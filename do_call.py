from autogen import ConversableAgent

from utils import  get_llms


_, llm_config_black = get_llms(
    black_hyperparams={"hyperparams": {"max_tokens": 16001}}) # Anthopic thinking throws if thinking budget is larger or equal to max tokens, easy verification of thinking budget

agent = ConversableAgent(
    name="test",
    llm_config=llm_config_black,
    max_consecutive_auto_reply=2,
    human_input_mode="NEVER",
)

response = agent.generate_reply(messages=[{"role": "user", "content": "Hello, how are you?"}])

print(response)
