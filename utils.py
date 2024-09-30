import os
from dotenv import load_dotenv

load_dotenv()


def get_llms():
    llm_config_white = {
        "api_type": "azure",
        "model": os.environ["AZURE_OPENAI_DEPLOYMENT_W"],
        "api_key": os.environ["AZURE_OPENAI_KEY_W"],
        "base_url": os.environ["AZURE_OPENAI_ENDPOINT_W"],
        "api_version": os.environ["AZURE_OPENAI_VERSION_W"],
    }

    llm_config_black = {
        "api_type": "azure",
        "model": os.environ["AZURE_OPENAI_DEPLOYMENT_B"],
        "api_key": os.environ["AZURE_OPENAI_KEY_B"],
        "base_url": os.environ["AZURE_OPENAI_ENDPOINT_B"],
        "api_version": os.environ["AZURE_OPENAI_VERSION_B"],
    }

    # Disabling LLM caching to avoid loops, also since the game is dynamic caching doesn't make sense
    llm_config_white["cache_seed"] = llm_config_black["cache_seed"] = None

    return llm_config_white, llm_config_black
