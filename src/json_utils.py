import json
from datapath import Register, Datapath
from asm_boxes import StateBox, DecisionBox, ConditionalBox


def load_asm_environment(filepath: str):
    with open(filepath, "r") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})

    outputs = metadata.get("outputs", [])
    initial_box = data.get("initial_box")
    testbench = data.get("testbench", {})
    raw_boxes = data.get("boxes", {})

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
        else:
            raise ValueError(f"Unknown box type identifier target: '{box_type}'")

    return datapath_obj, initial_box, box_map, testbench
