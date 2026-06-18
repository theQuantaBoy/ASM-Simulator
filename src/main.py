import os
import sys
from json_utils import load_asm_environment


def simulate_asm(json_filepath: str):
    if not os.path.exists(json_filepath):
        print(f"Error: Target simulation layout data path '{json_filepath}' not found.")
        return

    try:
        datapath, initial_box, box_map, testbench = load_asm_environment(json_filepath)

        total_cycles = testbench.get("total_cycles", 0)
        time_line = testbench.get("time_line", {})

        current_box_id = initial_box

        # Build layout columns for data report printing
        reg_names = list(datapath.registers.keys())
        input_names = list(datapath.inputs.keys())

        headers = ["Clock Cycle", "Active State"] + input_names + reg_names
        header_line = " | ".join(f"{h:<13}" for h in headers)

        print("\n" + "=" * len(header_line))
        print("               CYCLE ACCURATE ASM SIMULATION STATE REPORT")
        print("=" * len(header_line))
        print(header_line)
        print("-" * len(header_line))

        for i in range(total_cycles):
            cycle_str = str(i)

            # 1. Update external inputs at the start of the clock cycle
            if cycle_str in time_line:
                cycle_changes = time_line[cycle_str]
                for key, val in cycle_changes.items():
                    if key in datapath.inputs:
                        datapath.inputs[key] = val
                    elif key in datapath.registers:
                        datapath.registers[key].current_val = val
                        datapath.registers[key].next_val = val

            # 2. Combinational path traversal matching physical circuit propagation
            state_logged_this_cycle = current_box_id

            current_box = box_map[current_box_id]
            next_box_id = current_box.perform(datapath)

            # Continuous traversal through combinational elements (Decision/Conditional)
            while type(box_map[next_box_id]).__name__ != "StateBox":
                current_box = box_map[next_box_id]
                next_box_id = current_box.perform(datapath)

            # 3. Log active state variable metrics to output tracking table
            row_values = [str(i), state_logged_this_cycle]
            for inp in input_names:
                row_values.append(str(datapath.inputs[inp]))
            for reg in reg_names:
                row_values.append(str(datapath.registers[reg].current_val))

            print(" | ".join(f"{v:<13}" for v in row_values))

            # 4. Synchronous Clock Edge Trigger
            for reg in datapath.registers.values():
                reg.commit()

            # Assign state position target for the next cycle loop run
            current_box_id = next_box_id

        print("=" * len(header_line) + "\n")

    except Exception as e:
        print(f"\n[❌] Simulation runtime failure: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        simulate_asm(sys.argv[1])
    else:
        # Default test benchmark file path configuration
        simulate_asm("../data/asm_test.json")
