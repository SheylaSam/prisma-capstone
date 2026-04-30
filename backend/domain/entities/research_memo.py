from pydantic import BaseModel, ConfigDict, Field


class ContradictionItem(BaseModel):
    """Modell-zu-Modell-Widerspruch.

    Lebt hier (nicht im Schema-File), weil sowohl ResearchMemoSchema
    als auch ResearchMemo ihn nutzen.
    """

    model_config = ConfigDict(frozen=True)

    model_a: str = Field(..., min_length=1, max_length=64)
    model_b: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., max_length=200)
