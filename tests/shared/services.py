from oaas_sdk2_py.simplified import oaas, OaasObject, getter, setter
from pydantic import BaseModel


class Item(BaseModel):
    id: int
    name: str


@oaas.service("Counter", package="test")
class Counter(OaasObject):
    count: int = 0

    @oaas.method()
    def inc(self, by: int = 1) -> int:
        self.count += by
        return self.count

    @oaas.method(stateless=True)
    def peek(self) -> int:
        return self.count

    @getter("count")
    def get_count(self) -> int:
        return self.count

    @setter("count")
    def set_count(self, v: int) -> None:
        self.count = v


@oaas.service("Serializer", package="test")
class Serializer(OaasObject):
    item: Item | None = None

    @oaas.method()
    def set_item(self, item: Item) -> None:
        self.item = item

    @oaas.method(stateless=True)
    def get_item(self) -> Item | None:
        return self.item
