from __future__ import annotations

from aod._internal.testing.doubles.stubs import AsyncMethodStub, MethodStub


class TestMethodStub:
    def test_always_returns(self) -> None:
        stub = MethodStub()
        stub.always_returns(42)
        assert stub() == 42
        assert stub() == 42
        assert stub() == 42

    def test_always_returns_clears_returns(self) -> None:
        stub = MethodStub()
        stub.returns(1, 2)
        stub.always_returns(99)
        assert stub() == 99

    def test_returns_clears_always_returns(self) -> None:
        stub = MethodStub()
        stub.always_returns(99)
        stub.returns(1)
        assert stub() == 1
        assert stub() is None

    def test_call_with_kwargs(self) -> None:
        stub = MethodStub()
        stub.always_returns("ok")
        stub(a=1, b=2)
        assert stub.calls == [[1, 2]]

    def test_called_and_count_after_call(self) -> None:
        stub = MethodStub()
        assert stub.called is False
        assert stub.call_count == 0
        assert stub.calls == []
        stub()
        assert stub.called is True
        assert stub.call_count == 1
        assert stub.calls == [[]]

    def test_calls_returns_copy(self) -> None:
        stub = MethodStub()
        stub()
        calls = stub.calls
        calls.append(["x"])
        assert stub.calls == [[]]


class TestAsyncMethodStub:
    async def test_returns_clears_always_returns(self) -> None:
        stub = AsyncMethodStub()
        stub.always_returns(99)
        stub.returns(1, 2)
        r1 = await stub()
        r2 = await stub()
        r3 = await stub()
        assert r1 == 1
        assert r2 == 2
        assert r3 is None

    async def test_call_uses_returns_first(self) -> None:
        stub = AsyncMethodStub()
        stub.returns(10, 20)
        r1 = await stub()
        r2 = await stub()
        r3 = await stub()
        assert r1 == 10
        assert r2 == 20
        assert r3 is None

    async def test_always_returns_clears_returns(self) -> None:
        stub = AsyncMethodStub()
        stub.returns(1)
        stub.always_returns(99)
        assert await stub() == 99

    async def test_call_with_kwargs(self) -> None:
        stub = AsyncMethodStub()
        stub.always_returns("ok")
        result = await stub(x=1, y=2)
        assert result == "ok"
        assert stub.calls == [[1, 2]]

    async def test_called_property(self) -> None:
        stub = AsyncMethodStub()
        assert stub.called is False
        await stub()
        assert stub.called is True

    async def test_call_count_property(self) -> None:
        stub = AsyncMethodStub()
        assert stub.call_count == 0
        await stub()
        await stub()
        assert stub.call_count == 2

    async def test_calls_property(self) -> None:
        stub = AsyncMethodStub()
        await stub("a", "b")
        assert stub.calls == [["a", "b"]]

    async def test_calls_returns_copy(self) -> None:
        stub = AsyncMethodStub()
        await stub("a")
        calls = stub.calls
        calls.append(["x"])
        assert stub.calls == [["a"]]
