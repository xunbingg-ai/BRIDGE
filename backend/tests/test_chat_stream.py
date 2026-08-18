from fastapi.testclient import TestClient

from app.main import app


class FakeStream:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    def __aiter__(self):
        async def gen():
            for chunk in self._chunks:
                yield type(
                    "Chunk",
                    (),
                    {
                        "choices": [
                            type("Choice", (), {"delta": type("Delta", (), {"content": chunk})()})()
                        ]
                    },
                )()

        return gen()


class FakeCompletions:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeStream(self._chunks)


class FakeClient:
    def __init__(self, chunks: list[str]) -> None:
        self.completions = FakeCompletions(chunks)

    @property
    def chat(self):
        return self


def test_chat_stream_returns_sse_events():
    app.state.llm_client = FakeClient(["Hel", "lo", " there."])
    client = TestClient(app)
    response = client.post(
        "/api/chat/stream",
        json={
            "case_script": {"name": "Ms. Chen"},
            "history": [],
            "message": "Hi",
            "language": "en",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert body.startswith("data: Hel")
    assert "data: [DONE]" in body
    assert app.state.llm_client.completions.kwargs["stream"] is True
