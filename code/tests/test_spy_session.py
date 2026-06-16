from aod._internal.infrastructure.session import Session
from aod._internal.testing.doubles.infrastructure.session import session_stub


class SqlSession(Session):
    def execute(self, query: str) -> list[dict]:
        return []

    def find(self, entity_id: str) -> dict | None:
        return None

    def begin(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return False


class TestSpySession:
    def test_spy_session_inherits_from_user_session(self) -> None:
        MySpySession = session_stub(SqlSession)
        session = MySpySession()
        assert isinstance(session, SqlSession)

    def test_method_returns_configured_values(self) -> None:
        session = session_stub(SqlSession)()
        session.find.returns({"id": "1"}, {"id": "2"})
        assert session.find("1") == {"id": "1"}
        assert session.find("2") == {"id": "2"}

    def test_method_returns_none_when_exhausted(self) -> None:
        session = session_stub(SqlSession)()
        session.find.returns({"id": "1"})
        session.find("1")
        assert session.find("2") is None

    def test_method_tracks_calls(self) -> None:
        session = session_stub(SqlSession)()
        session.find("1")
        session.find("2")
        assert session.find.call_count == 2
        assert session.find.calls == [["1"], ["2"]]

    def test_method_called_property(self) -> None:
        session = session_stub(SqlSession)()
        assert not session.find.called
        session.find("1")
        assert session.find.called

    def test_multiple_methods(self) -> None:
        session = session_stub(SqlSession)()
        session.find.returns({"id": "1"})
        session.execute.returns([{"id": "1"}])
        assert session.find("1") == {"id": "1"}
        assert session.execute("SELECT * FROM users") == [{"id": "1"}]
        assert session.find.call_count == 1
        assert session.execute.call_count == 1
