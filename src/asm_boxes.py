from abc import ABC, abstractmethod
from typing import List, Dict
from instructions import MicroInstruction, Condition


class AbstractBox(ABC):
    def __init__(self, box_id: str):
        self.box_id = box_id

    @abstractmethod
    def perform(self, datapath) -> str:
        """
        Executes the box's logic using the datapath.
        Returns the string ID of the next box to transition to.
        """
        pass


class StateBox(AbstractBox):
    def __init__(self, box_id: str, actions: List[str], next_box: str):
        super().__init__(box_id)
        self.actions = [MicroInstruction(s) for s in actions]
        self.next_box = next_box

    def perform(self, datapath) -> str:
        for action in self.actions:
            action.execute(datapath)
        return self.next_box


class ConditionalBox(AbstractBox):
    def __init__(self, box_id: str, actions: List[str], next_box: str):
        super().__init__(box_id)
        self.actions = [MicroInstruction(s) for s in actions]
        self.next_box = next_box

    def perform(self, datapath) -> str:
        for action in self.actions:
            action.execute(datapath)
        return self.next_box


class DecisionBox(AbstractBox):
    def __init__(self, box_id: str, condition: str, branches: Dict[str, str]):
        super().__init__(box_id)
        self.condition = Condition(condition)
        self.branches = branches

    def perform(self, datapath) -> str:
        eval_result = self.condition.evaluate(datapath)
        eval_str = str(eval_result)

        if eval_str not in self.branches:
            raise ValueError(
                f"Branch evaluation result '{eval_str}' not mapped in box '{self.box_id}'"
            )
        return self.branches[eval_str]
