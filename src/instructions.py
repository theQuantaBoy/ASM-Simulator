from evaluator import ExpressionEvaluator


class MicroInstruction:
    def __init__(self, instruction: str):
        self.raw_instruction = instruction

    def execute(self, datapath) -> None:
        ExpressionEvaluator.execute_micro_instruction(self.raw_instruction, datapath)

    def __str__(self):
        return self.raw_instruction


class Condition:
    def __init__(self, condition: str):
        self.raw_condition = condition

    def evaluate(self, datapath) -> int:
        return ExpressionEvaluator.evaluate_rhs(self.raw_condition, datapath)

    def __str__(self):
        return self.raw_condition
