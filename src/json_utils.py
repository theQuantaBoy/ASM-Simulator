import json
from asm_boxes import StateBox, DecisionBox, ConditionalBox


def load_asm_environment(filepath: str):
    """
    Reads the JSON file and builds the simulation environment.
    Returns metadata, the initial box ID, the instantiated box map, and the testbench.
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    initial_box = data.get("initial_box")
    testbench = data.get("testbench", {})
    raw_boxes = data.get("boxes", {})

    box_map = {}

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
        else:
            raise ValueError(f"Unknown box type '{box_type}' in box {box_id}")

    return metadata, initial_box, box_map, testbench
