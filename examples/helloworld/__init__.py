import random
import string

from pydantic import BaseModel
from tsidpy import TSID

from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig


class GreetCreator(BaseModel):
    id: int = 0
    intro: str = "How are you?"


class GreetCreatorResponse(BaseModel):
    id: int
    

class Greet(BaseModel):
    name: str = "world"
    

class GreetResponse(BaseModel):
    message: str
    

class UpdateIntro(BaseModel):
    intro: str = "How are you?"


# Configure OaaS with simplified interface
config = OaasConfig(async_mode=True, mock_mode=False)
oaas.configure(config)


@oaas.service("Greeter", package="example")
class Greeter(OaasObject):
    """A greeting service that can personalize messages."""
    
    intro: str = "How are you?"

    @oaas.constructor()
    async def initialize(self, req: GreetCreator) -> GreetCreatorResponse:
        """Initialize a new greeter with custom intro."""
        if req.id == 0:
            req.id = TSID.create().number
        self.intro = req.intro
        return GreetCreatorResponse(id=req.id)

    @oaas.method()
    async def greet(self, req: Greet) -> GreetResponse:
        """Greet someone with a personalized message."""
        resp = f"hello {req.name}. {self.intro}"
        return GreetResponse(message=resp)

    @oaas.method()
    async def change_intro(self, req: UpdateIntro) -> None:
        """Change the greeting introduction."""
        self.intro = req.intro


class RandomRequest(BaseModel):
    entries: int = 10
    keys: int = 10
    values: int = 10


def generate_text(num: int) -> str:
    """Generate random text of specified length."""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(num))


@oaas.service("Record", package="example")
class Record(OaasObject):
    """A record service that can store and manipulate data."""
    
    record_data: dict = {}

    @oaas.method()
    async def random(self, req: RandomRequest) -> dict:
        """Generate random data and store it."""
        data = {}
        for _ in range(req.entries):
            data[generate_text(req.keys)] = generate_text(req.values)
        self.record_data = data
        return data
    
    @oaas.function()
    async def echo(self, data: str) -> str:
        """Echo back the provided data."""
        return data

    