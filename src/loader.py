import re
import json
from datapath import Register, Datapath
from asm_boxes import StateBox, DecisionBox, ConditionalBox

# ---------------------------------------------------------------------------
# ASM text parser
# ---------------------------------------------------------------------------


def _parse_width_declarations(content: str) -> dict:
    """Parse a comma-separated list of name<high:low> tokens into {name: width}."""
    tokens = re.findall(r"([a-zA-Z_]\w*)(?:<(\d+)[,:](\d+)>)?", content)
    return {
        name: abs(int(high) - int(low)) + 1 if high and low else 32
        for name, high, low in tokens
        if name
    }


def _parse_box_statement(stmt: str) -> tuple:
    """Parse a single box definition. Returns (box_id, box_dict) or None."""
    match = re.match(
        r"^([a-zA-Z_]\w*)\s*:\s*(STATE|CONDITIONAL|DECISION)\s*,\s*\{(.*?)\}\s*,\s*(.*)$",
        stmt,
        re.DOTALL,
    )
    if not match:
        return None

    box_id, box_type = match.group(1), match.group(2)
    inner, remainder = match.group(3).strip(), match.group(4).strip()

    if box_type in ("STATE", "CONDITIONAL"):
        return box_id, {
            "type": box_type,
            "actions": [a.strip() for a in inner.split(",") if a.strip()],
            "next": remainder,
        }

    # DECISION
    branches = {}
    for token in remainder.split(","):
        if ":" in token:
            k, v = token.split(":", 1)
            branches[k.strip()] = v.strip()
    return box_id, {"type": box_type, "condition": inner, "branches": branches}


def parse_asm_text(text: str) -> dict:
    """Parse raw ASM text grammar into a structured data dictionary."""
    asm_data = {
        "metadata": {"inputs": {}, "registers": {}, "outputs": []},
        "initial_box": None,
        "boxes": {},
    }

    for stmt in text.split(";"):
        stmt = stmt.strip()
        if not stmt:
            continue

        if stmt.startswith("INPUT"):
            asm_data["metadata"]["inputs"].update(_parse_width_declarations(stmt[5:]))
        elif stmt.startswith("REGISTER"):
            asm_data["metadata"]["registers"].update(
                _parse_width_declarations(stmt[8:])
            )
        elif stmt.startswith("OUTPUT"):
            asm_data["metadata"]["outputs"] = [
                s.strip() for s in stmt[6:].split(",") if s.strip()
            ]
        elif stmt.startswith("INITIAL"):
            asm_data["initial_box"] = stmt[7:].strip()
        else:
            result = _parse_box_statement(stmt)
            if result:
                box_id, box_dict = result
                asm_data["boxes"][box_id] = box_dict

    return asm_data


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_asm_design(filepath: str) -> dict:
    """Load an ASM description from a raw text file (.txt) or JSON file (.json)."""
    with open(filepath, "r") as f:
        if filepath.lower().endswith(".json"):
            return json.load(f)
        return parse_asm_text(f.read())


def load_testbench(filepath: str) -> dict:
    """Load a testbench JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Model builder
# ---------------------------------------------------------------------------


def _validate_graph(initial_box: str, box_map: dict, raw_boxes: dict) -> None:
    """Verify that all box references in the graph point to defined boxes."""
    if initial_box not in box_map:
        raise ValueError(
            f"INITIAL box '{initial_box}' is not defined in the ASM description."
        )

    for box_id, box_data in raw_boxes.items():
        box_type = box_data.get("type")
        if box_type in ("STATE", "CONDITIONAL"):
            target = box_data.get("next")
            if target not in box_map:
                raise ValueError(
                    f"Box '{box_id}' has undefined transition target '{target}'."
                )
        elif box_type == "DECISION":
            for branch_val, target in box_data.get("branches", {}).items():
                if target not in box_map:
                    raise ValueError(
                        f"Box '{box_id}' branch '{branch_val}' points to undefined box '{target}'."
                    )


def build_asm_model(asm_data: dict):
    """Instantiate the simulator's datapath and box graph from a parsed ASM data dict."""
    metadata = asm_data.get("metadata", {})
    initial_box = asm_data.get("initial_box")
    raw_boxes = asm_data.get("boxes", {})

    inputs = {name: 0 for name in metadata.get("inputs", {})}
    registers = {
        name: Register(name, w) for name, w in metadata.get("registers", {}).items()
    }
    datapath = Datapath(inputs, set(metadata.get("outputs", [])), registers)

    box_map = {}
    for box_id, box_data in raw_boxes.items():
        box_type = box_data.get("type")
        if box_type == "STATE":
            box_map[box_id] = StateBox(
                box_id, box_data.get("actions", []), box_data.get("next")
            )
        elif box_type == "CONDITIONAL":
            box_map[box_id] = ConditionalBox(
                box_id, box_data.get("actions", []), box_data.get("next")
            )
        elif box_type == "DECISION":
            box_map[box_id] = DecisionBox(
                box_id, box_data.get("condition"), box_data.get("branches", {})
            )

    _validate_graph(initial_box, box_map, raw_boxes)
    return datapath, initial_box, box_map
