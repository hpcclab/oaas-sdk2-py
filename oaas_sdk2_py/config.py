from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class OprcConfig(BaseSettings):
    oprc_odgm_url: HttpUrl = Field(default="http://localhost:10000")
    oprc_zenoh_peers: str|None = Field(default=None)
    oprc_partition_default: int = Field(default=0)
    
    def get_zenoh_peers(self) -> list[str]|None:
        if self.oprc_zenoh_peers is None:
            return None
        return self.oprc_zenoh_peers.split(",")