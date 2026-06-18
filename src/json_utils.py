import os
import re
import json
from datapath import Register, Datapath
from asm_boxes import StateBox, DecisionBox, ConditionalBox


def parse_asm_text(text: str) -> dict:
    """
    Parses raw ASM text grammar and translates it dynamically
    into a structured structural map dictionary.
    """
    asm_data = {
        "metadata": {"inputs": {}, "registers": {}, "outputs": []},
        "initial_box": None,
        "boxes": {},
    }

    # Split the full text content by semicolons to handle multi-line descriptions cleanly
    statements = text.split(";")

    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue

        if stmt.startswith("INPUT"):
            content = stmt[5:].strip()
            # Matches names aif stmt.startswith("INPUnd optional bit ranges like <31:0> or <31,0>
            tokens = re.findall(r"([a-zA-Z_]\w*)(?:<(\d+)[,:](\d+)>)?", content)
            for name, high, low in tokens:
                if name:
                    width = abs(int(high) - int(low)) + 1 if high and low else 32
                    asm_data["metadata"]["inputs"][name] = width

        elif stmt.startswith("REGISTER"):
            content = stmt[8:].strip()
            tokens = re.findall(r"([a-zA-Z_]\w*)(?:<(\d+)[,:](\d+)>)?", content)
            for name, high, low in tokens:
                if name:
                    width = abs(int(high) - int(low)) + 1 if high and low else 32
                    asm_data["metadata"]["registers"][name] = width

        elif stmt.startswith("OUTPUT"):
            content = stmt[6:].strip()
            asm_data["metadata"]["outputs"] = [
                out.strip() for out in content.split(",") if out.strip()
            ]

        elif stmt.startswith("INITIAL"):
            content = stmt[7:].strip()
            asm_data["initial_box"] = content

        else:
            # Matches Box ID, Type, content inside brackets {}, and trailing destination targets
            match = re.match(
                r"^([a-zA-Z_]\w*)\s*:\s*(STATE|CONDITIONAL|DECISION)\s*,\s*\{(.*?)\}\s*,\s*(.*)$",
                stmt,
                re.DOTALL,
            )
            if match:
                box_id = match.group(1)
                box_type = match.group(2)
                inner_bracket = match.group(3).strip()
                remainder = match.group(4).strip()

                box_dict = {"type": box_type}

                if box_type in ("STATE", "CONDITIONAL"):
                    actions = [a.strip() for a in inner_bracket.split(",") if a.strip()]
                    box_dict["actions"] = actions
                    box_dict["next"] = remainder
                elif box_type == "DECISION":
                    box_dict["condition"] = inner_bracket
                    branches = {}
                    # Parses branch paths like: 0:Box1, 1:Box3
                    for branch_token in remainder.split(","):
                        if ":" in branch_token:
                            k, v = branch_token.split(":", 1)
                            branches[k.strip()] = v.strip()
                    box_dict["branches"] = branches

                asm_data["boxes"][box_id] = box_dict

    return asm_data


def load_asm_design(filepath: str) -> dict:
    """
    Unified loader that reads an ASM description from either a raw text
    description (.txt) or a structured JSON architecture configuration (.json).
    """
    with open(filepath, "r") as f:
        if filepath.lower().endswith(".json"):
            return json.load(f)
        else:
            return parse_asm_text(f.read())


def build_asm_objects(asm_data: dict):
    """Factory builder that instantiates simulator components from an abstract data dict."""
    metadata = asm_data.get("metadata", {})
    outputs = metadata.get("outputs", [])
    initial_box = asm_data.get("initial_box")
    raw_boxes = asm_data.get("boxes", {})

    inputs = {}
    registers = {}
    box_map = {}

    for input_name in metadata.get("inputs", {}).keys():
        inputs[input_name] = 0

    for reg_name, width in metadata.get("registers", {}).items():
        registers[reg_name] = Register(reg_name, width)

    datapath_obj = Datapath(inputs, outputs, registers)

    for box_id, box_data in raw_boxes.items():
        box_type = box_data.get("type")

        if box_type == "STATE":
            box_map[box_id] = StateBox(
                box_id=box_id,
                actions=box_data.get("actions", []),
                next_box=box_data.get("next"),
            )
        elif box_type == "CONDITIONAL":
            box_map[box_id] = ConditionalBox(
                box_id=box_id,
                actions=box_data.get("actions", []),
                next_box=box_data.get("next"),
            )
        elif box_type == "DECISION":
            box_map[box_id] = DecisionBox(
                box_id=box_id,
                condition=box_data.get("condition"),
                branches=box_data.get("branches", {}),
            )

    return datapath_obj, initial_box, box_map


def load_testbench(filepath: str) -> dict:
    """Reads a completely standalone verification testbench file."""
    with open(filepath, "r") as f:
        return json.load(f)
