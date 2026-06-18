class Register:
    def __init__(self, name: str, width: int):
        self.name = name
        self.width = width
        self.current_val = 0
        self.next_val = 0
        self.should_change = False

    def set_next(self, value: int):
        mask = (1 << self.width) - 1
        self.next_val = value & mask
        self.should_change = True

    def commit(self):
        if self.should_change:
            self.current_val = self.next_val
        # Default future value preserves the current memory unless a new assignment occurs
        self.next_val = self.current_val
        self.should_change = False


class Datapath:
    def __init__(self, inputs: dict, outputs: list, registers: dict):
        self.inputs = inputs
        self.outputs = outputs
        self.registers = registers
