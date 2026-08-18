import asyncio
from types import SimpleNamespace

from app.services.sp.patient import SPResponder, build_sp_messages


SCRIPT = {
    "name": "Ms. Chen",
    "age": 32,
    "chief_complaint": "Recurrent chest pain on and off for 4 weeks.",
    "opening_statement": "I have had chest pain on and off for 4 weeks.",
    "disclosure_rules": ["Answer only from script."],
}


class FakeCompletions:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply))]
        )


class FakeClient:
    def __init__(self, reply: str = "I have had chest pain for 4 weeks.") -> None:
        self.completions = FakeCompletions(reply)

    @property
    def chat(self):
        return self


def test_build_sp_messages_include_script_and_constraints():
    messages = build_sp_messages(SCRIPT, [], "Do I have a heart attack?", "en")
    system, user = messages[0]["content"], messages[1]["content"]
    assert "Never fabricate" in system
    assert "case script" in system
    assert "Never give a diagnosis" in system
    assert "Recurrent chest pain on and off for 4 weeks." in user
    assert "Do I have a heart attack?" in user


def test_responder_calls_model_and_returns_reply():
    client = FakeClient(reply="I'm not sure. I just have this chest pain.")
    responder = SPResponder(client)  # type: ignore[arg-type]

    async def _run():
        return await responder.respond(SCRIPT, [], "What is wrong?", "en")

    reply = asyncio.run(_run())
    assert reply == "I'm not sure. I just have this chest pain."
    assert client.completions.kwargs["model"] == "deepseek-v4-flash"
    assert client.completions.kwargs["messages"][0]["role"] == "system"
