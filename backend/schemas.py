from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError


US_STATES = frozenset("""
AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD
MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC
SD TN TX UT VT VA WA WV WI WY
""".split())

PAGE_SIZE = 5

SortColumn = Literal["id", "name", "age", "birth_state"]
SortOrder = Literal["asc", "desc"]

class UserCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )
    name: str = Field(..., min_length=1, max_length=1000)
    age: int = Field(..., ge=0, le=32767)
    birth_state: str = Field(..., min_length=1, max_length=15)

    @field_validator("birth_state", mode="before")
    @classmethod
    def normalize_state(cls, value):
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("birth_state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        if value not in US_STATES:
            raise PydanticCustomError(
                "invalid_state",
                "Use a valid two-letter U.S. state code"
            )
        return value

class User(UserCreate):
    id: int

class UserUpdate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )
    name: str | None = Field(default=None, min_length=1, max_length=1000)
    age: int | None = Field(default=None, ge=0, le=32767)
    birth_state: str | None = Field(default=None, min_length=1, max_length=15)

    @field_validator("name", "age", "birth_state", mode="before")
    @classmethod
    def empty_str_to_none(cls, value):
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("birth_state", mode="before")
    @classmethod
    def normalize_state(cls, value):
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("birth_state")
    @classmethod
    def validate_state(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in US_STATES:
            raise PydanticCustomError(
                "invalid_state",
                "Use a valid two-letter U.S. state code"
            )
        return value