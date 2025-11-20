import random
import string

from pydantic import BaseModel
from tsidpy import TSID

from oaas_sdk2_py import oaas, OaasObject, OaasConfig


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


class SaveRecordEntry(BaseModel):
    key: str
    value: str


class WorkflowSetup(BaseModel):
    greeter_id: str
    record_id: str


class WorkflowInput(BaseModel):
    person: str
    intro_override: str | None = None
    note: str | None = None


class WorkflowResult(BaseModel):
    greeter_id: str
    record_id: str
    greeting: str
    log_snapshot: dict[str, str]


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

    @oaas.method()
    async def log_entry(self, req: SaveRecordEntry) -> dict[str, str]:
        """Persist a single entry into the record store."""
        snapshot = dict(self.record_data)
        snapshot[req.key] = req.value
        self.record_data = snapshot
        return snapshot

    @oaas.method()
    async def snapshot(self) -> dict[str, str]:
        """Return the latest stored entries."""
        return dict(self.record_data)


@oaas.service("ConversationWorkflow", package="example")
class ConversationWorkflow(OaasObject):
    """Coordinate Greeter and Record objects to form a mini workflow."""

    greeter_id: str | None = None
    record_id: str | None = None

    def _require_greeter(self) -> 'Greeter':
        if not self.greeter_id:
            raise ValueError("Greeter ID is not configured yet")
        return Greeter.load(self.greeter_id)

    def _require_record(self) -> 'Record':
        if not self.record_id:
            raise ValueError("Record ID is not configured yet")
        return Record.load(self.record_id)

    @oaas.method()
    async def configure(self, req: WorkflowSetup) -> WorkflowSetup:
        """Remember the cooperating Greeter and Record objects."""
        greeter = Greeter.load(req.greeter_id)
        record = Record.load(req.record_id)
        self.greeter_id = greeter.object_id
        self.record_id = record.object_id
        return WorkflowSetup(greeter_id=self.greeter_id, record_id=self.record_id)

    @oaas.method()
    async def run_workflow(self, req: WorkflowInput) -> WorkflowResult:
        """Invoke Greeter, then persist the outcome via Record."""
        greeter = self._require_greeter()
        record = self._require_record()

        if req.intro_override:
            await greeter.change_intro(UpdateIntro(intro=req.intro_override))

        greet_resp = await greeter.greet(Greet(name=req.person))
        note = req.note or greet_resp.message
        await record.log_entry(SaveRecordEntry(key=req.person, value=note))
        snapshot = await record.snapshot()

        return WorkflowResult(
            greeter_id=greeter.object_id,
            record_id=record.object_id,
            greeting=greet_resp.message,
            log_snapshot=snapshot,
        )

    