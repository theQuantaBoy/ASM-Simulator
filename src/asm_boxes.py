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
        self.actions = {MicroInstruction(s) for s in actions}
        self.next_box = next_box

    def perform(self, datapath) -> str:
        for action in self.actions:
            # TODO: Parse 'LHS <= RHS', evaluate RHS using datapath.current_val,
            # and stage the result to datapath.next_val
            pass
        return self.next_box


class ConditionalBox(AbstractBox):
    def __init__(self, box_id: str, actions: List[str], next_box: str):
        super().__init__(box_id)
        self.actions = {MicroInstruction(s) for s in actions}
        self.next_box = next_box

    def perform(self, datapath) -> str:
        for action in self.actions:
            # TODO: Same logic as StateBox. Stage assignments to next_val.
            pass


class DecisionBox(AbstractBox):
    def __init__(self, box_id: str, condition: str, branches: Dict[str, str]):
        super().__init__(box_id)
        self.condition = Condition(condition)
        self.branches = branches

    def perform(self, datapath) -> str:
        # TODO: Evaluate the condition string using datapath.current_val
        # For now, let's assume evaluation returns a string "0" or "1"
        eval_result = "0"  # Placeholder

        if eval_result not in self.branches:
            raise ValueError(
                f"Condition result '{eval_result}' not found in branches for {self.box_id}"
            )

        return self.branches[eval_result]
