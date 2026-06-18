import sys
import os

# Add the current directory to path if needed for package relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from json_utils import load_asm_environment


def run_sanity_check(json_filepath: str):
    print("--- Starting ASM Simulator Sanity Check ---")

    if not os.path.exists(json_filepath):
        print(f"Error: Target file '{json_filepath}' not found.")
        return

    try:
        # Load environment via the json_utils module
        metadata, initial_box, box_map, testbench = load_asm_environment(json_filepath)

        print("\n[+] JSON Parsing Successful!")
        print(f"Initial Box ID Target: {initial_box}")
        print(
            f"Total Simulation Cycles Requested: {testbench.get('total_cycles', 'Not Specified')}"
        )

        print("\n--- Parsed Datapath Metadata ---")
        print(f"Inputs detected: {list(metadata.get('inputs', {}).keys())}")
        print(f"Registers detected: {list(metadata.get('registers', {}).keys())}")
        print(f"Monitored Outputs: {metadata.get('outputs', [])}")

        print("\n--- Object Factory Instantiation Map ---")
        for box_id, box_obj in box_map.items():
            box_type = type(box_obj).__name__
            print(f" ID: {box_id:<8} | Instantiated Class: {box_type:<15}")

            # Print attributes to confirm wrappers work
            if hasattr(box_obj, "actions"):
                action_strs = [str(act) for act in box_obj.actions]
                print(f"   -> Actions found: {action_strs}")
            if hasattr(box_obj, "condition"):
                print(f"   -> Branch Condition: {box_obj.condition}")
            if hasattr(box_obj, "branches"):
                print(f"   -> Alternative Branches Map: {box_obj.branches}")
            if hasattr(box_obj, "next_box"):
                print(f"   -> Sequence Decoupled Next: {box_obj.next_box}")

        print(
            "\n[✔] Sanity Check Passed! Environment layout is ready for simulation execution logic."
        )

    except Exception as e:
        print(f"\n[❌] Sanity Check Failed due to an execution error: {e}")


if __name__ == "__main__":
    # Point this to wherever your structural divider JSON data file is stored
    target_json = "../data/asm_test.json"
    run_sanity_check(target_json)
