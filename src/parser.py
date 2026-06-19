import re


class ExpressionEvaluator:
    @staticmethod
    def clean_string(s: str) -> str:
        return s.strip(" ${}()")

    @staticmethod
    def resolve_operand(token: str, datapath) -> int:
        token = token.strip()
        if not token:
            return 0
        if token.isdigit():
            return int(token)
        if token in datapath.registers:
            return datapath.registers[token].current_val
        if token in datapath.inputs:
            return datapath.inputs[token]
        raise ValueError(f"Undeclared identifier or invalid operand token: '{token}'")

    @staticmethod
    def evaluate_rhs(rhs_str: str, datapath) -> int:
        rhs_str = ExpressionEvaluator.clean_string(rhs_str)

        # Master operator matcher sorted by length to prevent partial word/symbol splits
        op_pattern = r"(!=|==|>=|<=|<<|>>|>|<|\+|-|&|\||\^|~|\bAND\b|\bOR\b|\bXOR\b|\bNOT\b|\bshr\b|\bshl\b)"
        match = re.search(op_pattern, rhs_str, re.IGNORECASE)

        if not match:
            # Direct variable passthrough or pure constant number
            return ExpressionEvaluator.resolve_operand(rhs_str, datapath)

        op = match.group(1)
        op_upper = op.upper()
        left_part = rhs_str[: match.start()].strip()
        right_part = rhs_str[match.end() :].strip()

        # Scenario 1: Unary Operator (Left side of token split is empty)
        if not left_part:
            val = ExpressionEvaluator.resolve_operand(right_part, datapath)

            width = 32
            clean_token = right_part.strip()
            if clean_token in datapath.registers:
                width = datapath.registers[clean_token].width

            if op_upper in ("~", "NOT"):
                return (~val) & ((1 << width) - 1)
            elif op_upper in ("|", "OR"):
                return 0 if val == 0 else 1
            elif op_upper in ("&", "AND"):
                mask = (1 << width) - 1
                return 1 if (val & mask) == mask else 0
            elif op_upper == "SHR":
                return val >> 1
            elif op_upper == "SHL":
                return (val << 1) & ((1 << width) - 1)
            else:
                raise ValueError(f"Unsupported unary operator: '{op}'")

        # Scenario 2: Binary or Relational Operator
        else:
            val1 = ExpressionEvaluator.resolve_operand(left_part, datapath)
            val2 = ExpressionEvaluator.resolve_operand(right_part, datapath)

            if op == "+":
                return val1 + val2
            elif op == "-":
                return val1 - val2
            elif op_upper in ("&", "AND"):
                return val1 & val2
            elif op_upper in ("|", "OR"):
                return val1 | val2
            elif op_upper in ("^", "XOR"):
                return val1 ^ val2
            elif op == "<<":
                return val1 << val2
            elif op == ">>":
                return val1 >> val2
            elif op == "==":
                return 1 if val1 == val2 else 0
            elif op == ">":
                return 1 if val1 > val2 else 0
            elif op == "<":
                return 1 if val1 < val2 else 0
            elif op == ">=":
                return 1 if val1 >= val2 else 0
            elif op == "<=":
                return 1 if val1 <= val2 else 0
            elif op == "!=":
                return 1 if val1 != val2 else 0
            else:
                raise ValueError(f"Unsupported operational operator: '{op}'")

    @staticmethod
    def execute_micro_instruction(instruction_str: str, datapath):
        line = instruction_str.strip(" ${}")
        if not line:
            return

        if "<-" in line:
            lhs, rhs = line.split("<-", 1)
        elif "<=" in line:
            lhs, rhs = line.split("<=", 1)
        elif "=" in line:
            lhs, rhs = line.split("=", 1)
        else:
            raise ValueError(
                f"Invalid micro-instruction assignment formatting: '{instruction_str}'"
            )

        lhs_reg = lhs.strip()
        if lhs_reg not in datapath.registers:
            raise ValueError(
                f"Assignment target '{lhs_reg}' is not a declared Register element."
            )

        result_val = ExpressionEvaluator.evaluate_rhs(rhs, datapath)
        datapath.registers[lhs_reg].set_next(result_val)
