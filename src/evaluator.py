import re


class ExpressionEvaluator:

    @staticmethod
    def _clean(s: str) -> str:
        return s.strip(" ${}()")

    @staticmethod
    def _resolve(token: str, datapath) -> int:
        """Resolve a single token to its integer value."""
        token = token.strip()
        if not token:
            return 0
        if token.isdigit():
            return int(token)
        if token in datapath.registers:
            return datapath.registers[token].current_val
        if token in datapath.inputs:
            return datapath.inputs[token]
        raise ValueError(f"Undeclared identifier: '{token}'")

    @staticmethod
    def _eval_unary(op: str, val: int, width: int) -> int:
        op = op.upper()
        if op in ("~", "NOT"):
            return (~val) & ((1 << width) - 1)
        if op in ("|", "OR"):
            return 0 if val == 0 else 1
        if op in ("&", "AND"):
            return 1 if (val & ((1 << width) - 1)) == ((1 << width) - 1) else 0
        if op == "SHR":
            return val >> 1
        if op == "SHL":
            return (val << 1) & ((1 << width) - 1)
        raise ValueError(f"Unsupported unary operator: '{op}'")

    @staticmethod
    def _eval_binary(op: str, val1: int, val2: int) -> int:
        op = op.upper()
        if op == "+":
            return val1 + val2
        if op == "-":
            return val1 - val2
        if op in ("&", "AND"):
            return val1 & val2
        if op in ("|", "OR"):
            return val1 | val2
        if op in ("^", "XOR"):
            return val1 ^ val2
        if op == "<<":
            return val1 << val2
        if op == ">>":
            return val1 >> val2
        if op == "==":
            return int(val1 == val2)
        if op == "!=":
            return int(val1 != val2)
        if op == ">":
            return int(val1 > val2)
        if op == "<":
            return int(val1 < val2)
        if op == ">=":
            return int(val1 >= val2)
        if op == "<=":
            return int(val1 <= val2)
        raise ValueError(f"Unsupported binary operator: '{op}'")

    @staticmethod
    def evaluate_rhs(rhs_str: str, datapath) -> int:
        rhs_str = ExpressionEvaluator._clean(rhs_str)

        # Operator pattern — longer tokens listed first to prevent partial matches
        op_pattern = r"(!=|==|>=|<=|<<|>>|>|<|\+|-|&|\||\^|~|\bAND\b|\bOR\b|\bXOR\b|\bNOT\b|\bshr\b|\bshl\b)"
        match = re.search(op_pattern, rhs_str, re.IGNORECASE)

        if not match:
            return ExpressionEvaluator._resolve(rhs_str, datapath)

        op = match.group(1)
        left = rhs_str[: match.start()].strip()
        right = rhs_str[match.end() :].strip()

        if not left:
            # Unary operator
            val = ExpressionEvaluator._resolve(right, datapath)
            width = (
                datapath.registers[right].width if right in datapath.registers else 32
            )
            return ExpressionEvaluator._eval_unary(op, val, width)
        else:
            # Binary operator
            val1 = ExpressionEvaluator._resolve(left, datapath)
            val2 = ExpressionEvaluator._resolve(right, datapath)
            return ExpressionEvaluator._eval_binary(op, val1, val2)

    @staticmethod
    def execute_micro_instruction(instruction_str: str, datapath):
        line = instruction_str.strip(" ${}")
        if not line:
            return

        for sep in ("<-", "<=", "="):
            if sep in line:
                lhs, rhs = line.split(sep, 1)
                break
        else:
            raise ValueError(f"Invalid micro-instruction: '{instruction_str}'")

        lhs_reg = lhs.strip()
        if lhs_reg not in datapath.registers:
            raise ValueError(
                f"Assignment target '{lhs_reg}' is not a declared register."
            )

        datapath.registers[lhs_reg].set_next(
            ExpressionEvaluator.evaluate_rhs(rhs, datapath)
        )
