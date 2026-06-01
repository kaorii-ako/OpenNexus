import pytest
import respx
import httpx
from backend.core.engine import OllamaEngine


@pytest.fixture
def engine():
    return OllamaEngine(base_url="http://localhost:11434", model="qwen2.5:7b", embed_model="nomic-embed-text")


@respx.mock
@pytest.mark.asyncio
async def test_embed(engine):
    respx.post("http://localhost:11434/api/embeddings").mock(
        return_value=httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3]})
    )
    result = await engine.embed("hello world")
    assert result == [0.1, 0.2, 0.3]


@respx.mock
@pytest.mark.asyncio
async def test_chat_non_stream(engine):
    respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(200, json={
            "message": {"role": "assistant", "content": "Hello!"},
            "done": True
        })
    )
    result = await engine.chat([{"role": "user", "content": "hi"}], stream=False)
    assert result == "Hello!"


@respx.mock
@pytest.mark.asyncio
async def test_model_routing_code(engine):
    engine.set_models(code="qwen2.5-coder:7b", reasoning="deepseek-r1:7b")
    assert engine.route_model("/code fix this bug") == "qwen2.5-coder:7b"


@respx.mock
@pytest.mark.asyncio
async def test_model_routing_think(engine):
    engine.set_models(code="qwen2.5-coder:7b", reasoning="deepseek-r1:7b")
    assert engine.route_model("/think about this") == "deepseek-r1:7b"


def test_model_routing_default(engine):
    engine.set_models(code="qwen2.5-coder:7b", reasoning="deepseek-r1:7b")
    assert engine.route_model("just a normal question") == "qwen2.5:7b"
