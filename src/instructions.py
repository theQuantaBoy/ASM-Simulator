class MicroInstruction:
    def __init__(self, instruction: str):
        self.raw_instruction = instruction

    def __str__(self):
        return self.raw_instruction


class Condition:
    def __init__(self, condition: str):
        self.raw_condition = condition

    def __str__(self):
        return self.raw_condition
