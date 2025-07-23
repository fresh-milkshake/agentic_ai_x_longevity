from agents import OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from src.constants import LLAMA_API_ENDPOINT

_ollama_client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
_g4f_client = AsyncOpenAI(base_url="http://localhost:1337/v1", api_key="")
_openai_client = AsyncOpenAI(base_url="https://api.openai.com/v1", api_key="")
_custom_llama_server = AsyncOpenAI(base_url=LLAMA_API_ENDPOINT, api_key="dummy-key")

_client = _ollama_client # _custom_llama_server

Qwen3 = OpenAIChatCompletionsModel(
    model="qwen3",
    openai_client=_client
)

Llama32 = OpenAIChatCompletionsModel( 
    model="llama3.2",
    openai_client=_client
)

Llama33 = OpenAIChatCompletionsModel(
    model="llama-3.3-70b-instruct",
    openai_client=_client
)

Gpt4o = OpenAIChatCompletionsModel(
    model="gpt-4o",
    openai_client=_client
)

Gpt4oMini = OpenAIChatCompletionsModel(
    model="gpt-4o-mini",
    openai_client=_client
)

DEFAULT_MODEL = Qwen3