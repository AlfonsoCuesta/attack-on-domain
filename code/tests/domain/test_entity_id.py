from __future__ import annotations

from aod.domain import EntityId, ValueObject


class UserId(EntityId):
    email: str
    phone: str


class OrderId(EntityId):
    value: str


class TestEntityIdCreation:
    def test_simple_identity(self) -> None:
        uid = UserId(email="a@b.com", phone="123")
        assert uid.email == "a@b.com"
        assert uid.phone == "123"
        assert uid.last_id is None

    def test_is_value_object(self) -> None:
        assert issubclass(EntityId, ValueObject)
        assert isinstance(UserId(email="a@b.com", phone="123"), ValueObject)


class TestEntityIdEquality:
    def test_equal_values(self) -> None:
        assert UserId(email="a@b.com", phone="123") == UserId(email="a@b.com", phone="123")

    def test_different_values(self) -> None:
        assert UserId(email="a@b.com", phone="123") != UserId(email="other@b.com", phone="123")

    def test_different_type(self) -> None:
        uid = UserId(email="a@b.com", phone="123")
        oid = OrderId(value="abc")
        assert uid != oid

    def test_self_equality(self) -> None:
        uid = UserId(email="a@b.com", phone="123")
        assert uid == uid


class TestEntityIdEvolve:
    def test_evolve_changes_field(self) -> None:
        uid1 = UserId(email="a@b.com", phone="123")
        uid2 = uid1.evolve(email="new@b.com")

        assert uid2.email == "new@b.com"
        assert uid2.phone == "123"

    def test_evolve_keeps_unchanged_fields(self) -> None:
        uid1 = UserId(email="a@b.com", phone="123")
        uid2 = uid1.evolve(email="new@b.com")

        assert uid2.phone == uid1.phone

    def test_evolve_setslast_id_to_original(self) -> None:
        uid1 = UserId(email="a@b.com", phone="123")
        uid2 = uid1.evolve(email="new@b.com")

        assert uid2.last_id is uid1

    def test_evolve_chain_points_to_oldest(self) -> None:
        uid1 = UserId(email="a@b.com", phone="123")
        uid2 = uid1.evolve(email="new@b.com")
        uid3 = uid2.evolve(phone="456")

        assert uid3.last_id is uid1
        assert uid3.email == "new@b.com"
        assert uid3.phone == "456"

    def test_evolve_returns_new_instance(self) -> None:
        uid1 = UserId(email="a@b.com", phone="123")
        uid2 = uid1.evolve(email="new@b.com")

        assert uid2 is not uid1

    def test_evolve_no_changes_creates_same_values(self) -> None:
        uid1 = UserId(email="a@b.com", phone="123")
        uid2 = uid1.evolve(email="a@b.com", phone="123")

        assert uid2.email == uid1.email
        assert uid2.phone == uid1.phone


class TestEntityIdHash:
    def test_equal_objects_have_same_hash(self) -> None:
        h1 = hash(UserId(email="a@b.com", phone="123"))
        h2 = hash(UserId(email="a@b.com", phone="123"))
        assert h1 == h2

    def test_hashable_in_set(self) -> None:
        s = {UserId(email="a@b.com", phone="123")}
        assert UserId(email="a@b.com", phone="123") in s

    def test_hashable_in_dict(self) -> None:
        d = {UserId(email="a@b.com", phone="123"): "user1"}
        assert d[UserId(email="a@b.com", phone="123")] == "user1"


class TestEntityIdReconstruct:
    def test_reconstruct_skips_validation(self) -> None:
        uid = UserId.reconstruct(email="x", phone="y")
        assert isinstance(uid, UserId)
        assert uid.email == "x"


class TestEntityIdImmutability:
    def test_cannot_mutate_field(self) -> None:
        uid = UserId(email="a@b.com", phone="123")
        try:
            uid.email = "other@b.com"  # type: ignore[misc]
            assert False, "should have raised"
        except Exception:
            pass

    def test_cannot_mutatelast_id(self) -> None:
        uid = UserId(email="a@b.com", phone="123")
        try:
            uid.last_id = None  # type: ignore
            assert False, "should have raised"
        except Exception:
            pass


class TestEntityIdMultipleTypes:
    def test_different_entity_id_types_are_independent(self) -> None:
        class ProductId(EntityId):
            sku: str

        pid = ProductId(sku="ABC-123")
        assert pid.sku == "ABC-123"
        assert isinstance(pid, EntityId)
