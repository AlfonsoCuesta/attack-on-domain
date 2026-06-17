from __future__ import annotations

from aod._internal.application.handler.handler import HandlerProtocol


class TestHandlerProtocol:
    def test_subclass_without_handle_does_not_crash(self) -> None:
        class _NoHandle(HandlerProtocol):
            pass

        assert issubclass(_NoHandle, HandlerProtocol)

    def test_subclass_with_handle_works(self) -> None:
        class _WithHandle(HandlerProtocol):
            def handle(self, cmd: object) -> None:
                pass

        assert hasattr(_WithHandle, "handle")
