import os
import argparse
from loader import load_asm_design, build_asm_model, load_testbench
from asm_boxes import StateBox
from vcd_logger import VcdLogger


def validate_input_files(asm_filepath: str, testbench_filepath: str) -> bool:
    """Return True only when both required files are present on disk."""
    if not os.path.exists(asm_filepath):
        print(f"Error: ASM description file '{asm_filepath}' not found.")
        return False
    if not os.path.exists(testbench_filepath):
        print(f"Error: Testbench verification file '{testbench_filepath}' not found.")
        return False
    return True


def resolve_cycle_budget(testbench_filepath: str, timeout_limit: int) -> tuple:
    """
    Load the testbench and determine how many cycles to simulate.

    Priority:
      1. --timeout flag      → run exactly N cycles, no early exit.
      2. total_cycles field  → run exactly N cycles, no early exit.
      3. Neither present     → adaptive mode: run until the design returns
                               to its initial state after all stimuli, with
                               a minimum floor of 40 cycles.

    Returns: (time_line, max_cycles, early_exit_enabled, last_change)
    """
    testbench = load_testbench(testbench_filepath)
    time_line = testbench.get("time_line", {})
    last_change = max((int(c) for c in time_line), default=0)

    if timeout_limit is not None:
        return time_line, timeout_limit, False, last_change
    elif "total_cycles" in testbench:
        return time_line, testbench["total_cycles"], False, last_change
    else:
        return time_line, max(last_change, 40), True, last_change


def apply_testbench_inputs(cycle_idx: int, time_line: dict, datapath) -> None:
    """Drive any input or register overrides scheduled for this cycle."""
    for key, val in time_line.get(str(cycle_idx), {}).items():
        if key in datapath.inputs:
            datapath.inputs[key] = val
        elif key in datapath.registers:
            # Direct override bypasses set_next so it takes effect immediately
            datapath.registers[key].current_val = val
            datapath.registers[key].next_val = val


def build_report_header(
    asm_filepath: str,
    testbench_filepath: str,
    tracked_inputs: list,
    tracked_registers: list,
) -> tuple[str, str]:
    """Build and print the report title and column headers. Returns (header_line, sep)."""
    headers = ["Clock Cycle", "Active State"] + tracked_inputs + tracked_registers
    header_line = " | ".join(f"{h:<13}" for h in headers)
    sep = "-" * len(header_line)

    print("\n" + "=" * len(header_line))
    print(
        f"   CYCLE ACCURATE REPORT: {os.path.basename(asm_filepath)} [{os.path.basename(testbench_filepath)}]"
    )
    print("=" * len(header_line))
    print(header_line)
    print(sep)

    return header_line, sep


def print_cycle_row(
    cycle_idx: int,
    state_id: str,
    tracked_inputs: list,
    tracked_registers: list,
    datapath,
) -> None:
    """Print one row of the cycle-accurate signal table."""
    row_values = [str(cycle_idx), state_id]
    for inp in tracked_inputs:
        row_values.append(str(datapath.inputs[inp]))
    for reg in tracked_registers:
        row_values.append(str(datapath.registers[reg].current_val))
    print(" | ".join(f"{v:<13}" for v in row_values))


def simulate_asm(
    asm_filepath: str,
    testbench_filepath: str,
    show_all: bool = False,
    timeout_limit: int = None,
    vcd_filepath: str = None,
):
    if not validate_input_files(asm_filepath, testbench_filepath):
        return

    vcd_logger = None
    try:
        # --- Build the hardware model ---
        asm_data = load_asm_design(asm_filepath)
        datapath, initial_box, box_map = build_asm_model(asm_data)

        # --- Optionally start waveform tracing ---
        if vcd_filepath:
            vcd_filepath = os.path.join(
                os.path.dirname(os.path.abspath(asm_filepath)),
                os.path.basename(vcd_filepath),
            )
            input_widths = asm_data.get("metadata", {}).get("inputs", {})
            vcd_logger = VcdLogger(vcd_filepath, datapath, box_map, input_widths)
            print(f"[⚙️] Waveform tracer online: '{vcd_filepath}'")

        # --- Load testbench and determine cycle budget ---
        time_line, max_cycles, early_exit_enabled, last_change = resolve_cycle_budget(
            testbench_filepath, timeout_limit
        )

        # --- Decide which signals to display ---
        if show_all:
            tracked_inputs = list(datapath.inputs.keys())
            tracked_registers = list(datapath.registers.keys())
        else:
            tracked_inputs = [s for s in datapath.inputs if s in datapath.outputs]
            tracked_registers = [s for s in datapath.registers if s in datapath.outputs]

        # --- Print report header ---
        header_line, sep = build_report_header(
            asm_filepath, testbench_filepath, tracked_inputs, tracked_registers
        )

        # --- Cycle-accurate simulation loop ---
        current_box_id = initial_box
        has_left_initial = False

        for i in range(max_cycles):

            apply_testbench_inputs(i, time_line, datapath)

            if vcd_logger:
                vcd_logger.log_cycle(i, current_box_id)

            if current_box_id != initial_box:
                has_left_initial = True

            terminate_after_this_cycle = (
                early_exit_enabled
                and has_left_initial
                and current_box_id == initial_box
                and i > last_change
            )

            next_box_id = box_map[current_box_id].perform(datapath)
            while not isinstance(box_map[next_box_id], StateBox):
                next_box_id = box_map[next_box_id].perform(datapath)

            print_cycle_row(
                i, current_box_id, tracked_inputs, tracked_registers, datapath
            )

            for reg in datapath.registers.values():
                reg.apply()

            current_box_id = next_box_id

            if terminate_after_this_cycle:
                print(sep)
                print(
                    f"[ℹ️] Early termination at cycle {i}: returned to '{initial_box}' past last stimulus (cycle {last_change})."
                )
                break

        else:
            if early_exit_enabled:
                print(sep)
                print(
                    f"[⚠️] Watchdog timeout: reached {max_cycles} cycles without returning to initial state."
                )

        print("=" * len(header_line) + "\n")

    except Exception as e:
        import traceback

        print(f"\n[❌] Simulation error: {e}")
        traceback.print_exc()

    finally:
        if vcd_logger:
            vcd_logger.close()
            print("[💾] Waveform file saved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cycle-Accurate ASM Simulator.")
    parser.add_argument(
        "asm_file",
        nargs="?",
        default="data/divider.txt",
        help="ASM description file (.txt or .json).",
    )
    parser.add_argument(
        "testbench_file",
        nargs="?",
        default="data/tb_divider_01.json",
        help="Testbench JSON file.",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Show all signals, not just declared outputs.",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=None,
        help="Run for exactly this many cycles.",
    )
    parser.add_argument(
        "--vcd",
        nargs="?",
        const="waves.vcd",
        default=None,
        help="Write a VCD waveform file (default name: waves.vcd).",
    )

    args = parser.parse_args()
    simulate_asm(
        args.asm_file,
        args.testbench_file,
        show_all=args.all,
        timeout_limit=args.timeout,
        vcd_filepath=args.vcd,
    )
