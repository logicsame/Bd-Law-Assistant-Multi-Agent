
from typing import TypedDict,Annotated
import operator


class AgentState(TypedDict):
    query: str
    documents: list
    classification: dict
    analysis: str
    follow_ups: list
    conversation_history: Annotated[list, operator.add]
    current_step: str