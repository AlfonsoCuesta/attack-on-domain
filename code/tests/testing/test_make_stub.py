from aod.application import Port
from aod.testing.doubles import port_stub, MethodStub


class EmailGateway(Port):
    def send(self, to: str, subject: str, body: str) -> bool:
        return True

    def validate(self, email: str) -> bool:
        return "@" in email


class TestPortStub:
    def test_stub_inherits_from_port(self) -> None:
        StubEmailGateway = port_stub(EmailGateway)
        assert issubclass(StubEmailGateway, EmailGateway)

    def test_stub_methods_are_configurable(self) -> None:
        StubEmailGateway = port_stub(EmailGateway)
        stub = StubEmailGateway()
        stub.send.returns(True, False)
        assert stub.send("a@b.com", "Hi", "Body") is True
        assert stub.send("c@d.com", "Hi", "Body") is False

    def test_stub_methods_return_none_when_exhausted(self) -> None:
        StubEmailGateway = port_stub(EmailGateway)
        stub = StubEmailGateway()
        stub.send.returns(True)
        stub.send("a@b.com", "Hi", "Body")
        assert stub.send("b@c.com", "Hi", "Body") is None

    def test_stub_methods_track_calls(self) -> None:
        StubEmailGateway = port_stub(EmailGateway)
        stub = StubEmailGateway()
        stub.send("a@b.com", "Hi", "Body")
        stub.send("c@d.com", "Hi", "Body")
        assert stub.send.call_count == 2
        assert stub.send.calls == [["a@b.com", "Hi", "Body"], ["c@d.com", "Hi", "Body"]]

    def test_stub_multiple_methods(self) -> None:
        StubEmailGateway = port_stub(EmailGateway)
        stub = StubEmailGateway()
        stub.send.returns(True)
        stub.validate.returns(False)
        assert stub.send("a@b.com", "Hi", "Body") is True
        assert stub.validate("a@b.com") is False
        assert stub.send.call_count == 1
        assert stub.validate.call_count == 1

    def test_stub_is_method_stub(self) -> None:
        StubEmailGateway = port_stub(EmailGateway)
        stub = StubEmailGateway()
        assert isinstance(stub.send, MethodStub)
