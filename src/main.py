import os
import sys
import argparse
from json_utils import load_asm_design, build_asm_objects, load_testbench


def simulate_asm(
    asm_filepath: str,
    testbench_filepath: str,
    show_all: bool = False,
    timeout_limit: int = None,
):
    if not os.path.exists(asm_filepath):
        print(f"Error: ASM description file '{asm_filepath}' not found.")
        return
    if not os.path.exists(testbench_filepath):
        print(f"Error: Testbench verification file '{testbench_filepath}' not found.")
        return

    try:
        # 1. Load and instantiate hardware model
        asm_data = load_asm_design(asm_filepath)
        datapath, initial_box, box_map = build_asm_objects(asm_data)

        # 2. Extract verification metadata and determine exact simulation cycles
        testbench = load_testbench(testbench_filepath)
        time_line = testbench.get("time_line", {})

        # Calculate timeline bounds to see when the last input stimulus happens
        if time_line:
            last_change = max(int(cycle) for cycle in time_line.keys())
        else:
            last_change = 0

        # Determine execution behavior and cycle limits
        if timeout_limit is not None:
            max_cycles = timeout_limit
            early_exit_enabled = False
        elif "total_cycles" in testbench:
            max_cycles = testbench["total_cycles"]
            early_exit_enabled = False
        else:
            # Neither specified: Run adaptively with a safe fallback floor of 40 cycles
            max_cycles = max(last_change, 40)
            early_exit_enabled = True

        # 3. Setup reporting columns based on display flags
        if show_all:
            tracked_inputs = list(datapath.inputs.keys())
            tracked_registers = list(datapath.registers.keys())
        else:
            tracked_inputs = [inp for inp in datapath.inputs if inp in datapath.outputs]
            tracked_registers = [
                reg for reg in datapath.registers if reg in datapath.outputs
            ]

        headers = ["Clock Cycle", "Active State"] + tracked_inputs + tracked_registers
        header_line = " | ".join(f"{h:<13}" for h in headers)

        print("\n" + "=" * len(header_line))
        print(
            f"   CYCLE ACCURATE REPORT: {os.path.basename(asm_filepath)} [{os.path.basename(testbench_filepath)}]"
        )
        print("=" * len(header_line))
        print(header_line)
        print("-" * len(header_line))

        # 4. Initialize simulation environment states
        current_box_id = initial_box
        has_left_initial = False

        for i in range(max_cycles):
            cycle_str = str(i)

            # Update incoming environment signal traces on current clock level
            if cycle_str in time_line:
                cycle_changes = time_line[cycle_str]
                for key, val in cycle_changes.items():
                    if key in datapath.inputs:
                        datapath.inputs[key] = val
                    elif key in datapath.registers:
                        datapath.registers[key].current_val = val
                        datapath.registers[key].next_val = val

            # Check if execution path has branched away from initialization node
            if current_box_id != initial_box:
                has_left_initial = True

            # Evaluate Early Termination criteria for the *upcoming* state landing step
            terminate_after_this_cycle = False
            if (
                early_exit_enabled
                and has_left_initial
                and current_box_id == initial_box
                and i > last_change
            ):
                terminate_after_this_cycle = True

            # Combinational path propagation logic loop
            state_logged_this_cycle = current_box_id
            current_box = box_map[current_box_id]
            next_box_id = current_box.perform(datapath)

            while type(box_map[next_box_id]).__name__ != "StateBox":
                current_box = box_map[next_box_id]
                next_box_id = current_box.perform(datapath)

            # Print state data metrics record row
            row_values = [str(i), state_logged_this_cycle]
            for inp in tracked_inputs:
                row_values.append(str(datapath.inputs[inp]))
            for reg in tracked_registers:
                row_values.append(str(datapath.registers[reg].current_val))
            print(" | ".join(f"{v:<13}" for v in row_values))

            # Synchronous Clock Edge Trigger Commit
            for reg in datapath.registers.values():
                reg.commit()

            # Set up state positioning for next loop cycle evaluation
            current_box_id = next_box_id

            if terminate_after_this_cycle:
                print("-" * len(header_line))
                print(
                    f"[ℹ️] Early Termination: Gracefully stopped at cycle {i}. System safely returned"
                )
                print(
                    f"    to resting state '{initial_box}' past last command change (cycle {last_change})."
                )
                break

        else:
            if early_exit_enabled:
                print("-" * len(header_line))
                print(
                    f"[⚠️] Watchdog Timeout: Reached max limit of {max_cycles} cycles without returning to initial state."
                )

        print("=" * len(header_line) + "\n")

    except Exception as e:
        import traceback

        print(f"\n[❌] Simulation runtime failure: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cycle-Accurate Hardware ASM Simulator Engine."
    )

    parser.add_argument(
        "asm_file",
        nargs="?",
        default="data/divider.txt",
        help="Path to ASM structure file (.txt raw grammar OR .json configuration text).",
    )
    parser.add_argument(
        "testbench_file",
        nargs="?",
        default="data/tb_divider_01.json",
        help="Path to the standalone verification testbench JSON file.",
    )

    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Display all internal signals rather than filtering by OUTPUT descriptions.",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=None,
        help="Force execution for this exact number of cycles, overriding adaptive modes.",
    )

    args = parser.parse_args()
    simulate_asm(
        args.asm_file,
        args.testbench_file,
        show_all=args.all,
        timeout_limit=args.timeout,
    )
