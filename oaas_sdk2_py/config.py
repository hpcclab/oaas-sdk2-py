import os

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class OprcConfig(BaseSettings):
    oprc_odgm_url: HttpUrl = Field(default="http://localhost:10000")