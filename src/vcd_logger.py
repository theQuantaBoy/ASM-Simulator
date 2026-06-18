import datetime


class VcdLogger:
    """
    Generates an IEEE-1364 standard Value Change Dump (.vcd) trace file
    capturing clock transitions, state transitions, inputs, and internal registers.
    """

    def __init__(self, filename: str, datapath, box_map, input_widths: dict):
        self.filename = filename
        self.datapath = datapath
        self.box_map = box_map
        self.input_widths = input_widths
        self.file = open(filename, "w")

        # Enumerate all ASM boxes to assign unique integer tokens for waveform state data buses
        self.state_to_idx = {box_id: idx for idx, box_id in enumerate(box_map.keys())}
        self.state_width = max(
            8, max(self.state_to_idx.values(), default=0).bit_length()
        )

        self.symbols = {}
        self._write_header()

    def _format_vcd_val(self, val: int, width: int) -> str:
        mask = (1 << width) - 1
        val = val & mask
        if width == 1:
            return f"{val}"
        return f"b{bin(val)[2:]} "

    def _write_header(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.file.write(f"$date\n   {timestamp}\n$end\n")
        self.file.write("$version\n   QuantaASM Simulator VCD Engine\n$end\n")
        self.file.write("$timescale 1ns $end\n")
        self.file.write("$scope module tb_top $end\n")

        ascii_cursor = 33  # Character '!' as initial shorthand VCD token alias

        # 1. System Clock
        self.symbols["clk"] = chr(ascii_cursor)
        self.file.write(f"$var wire 1 {chr(ascii_cursor)} clk $end\n")
        ascii_cursor += 1

        # 2. Simulator Execution Step State Identifier
        self.symbols["active_box"] = chr(ascii_cursor)
        self.file.write(
            f"$var wire {self.state_width} {chr(ascii_cursor)} active_box_id $end\n"
        )
        ascii_cursor += 1

        # 3. Structural Port Inputs
        for name in self.datapath.inputs.keys():
            width = self.input_widths.get(name, 32)
            self.symbols[f"in_{name}"] = chr(ascii_cursor)
            self.file.write(f"$var wire {width} {chr(ascii_cursor)} {name} $end\n")
            ascii_cursor += 1

        # 4. Hardware Synchronous Registers
        for name, reg in self.datapath.registers.items():
            self.symbols[f"reg_{name}"] = chr(ascii_cursor)
            self.file.write(f"$var wire {reg.width} {chr(ascii_cursor)} {name} $end\n")
            ascii_cursor += 1

        self.file.write("$upscope $end\n$enddefinitions\n$dumpvars\n")

        # Output Initial Signal Dumps at t=0
        self.file.write(f"0{self.symbols['clk']}\n")
        self.file.write(
            f"{self._format_vcd_val(0, self.state_width)}{self.symbols['active_box']}\n"
        )
        for name in self.datapath.inputs.keys():
            width = self.input_widths.get(name, 32)
            self.file.write(
                f"{self._format_vcd_val(0, width)}{self.symbols[f'in_{name}']}\n"
            )
        for name, reg in self.datapath.registers.items():
            self.file.write(
                f"{self._format_vcd_val(0, reg.width)}{self.symbols[f'reg_{name}']}\n"
            )
        self.file.write("$end\n")

    def log_cycle(self, cycle_num: int, active_box_id: str):
        time_base = cycle_num * 10

        # --- Rising Edge Event Activation (clk = 1) ---
        self.file.write(f"#{time_base}\n")
        self.file.write(f"1{self.symbols['clk']}\n")

        state_idx = self.state_to_idx.get(active_box_id, 0)
        self.file.write(
            f"{self._format_vcd_val(state_idx, self.state_width)}{self.symbols['active_box']}\n"
        )

        for name, val in self.datapath.inputs.items():
            width = self.input_widths.get(name, 32)
            self.file.write(
                f"{self._format_vcd_val(val, width)}{self.symbols[f'in_{name}']}\n"
            )

        for name, reg in self.datapath.registers.items():
            self.file.write(
                f"{self._format_vcd_val(reg.current_val, reg.width)}{self.symbols[f'reg_{name}']}\n"
            )

        # --- Falling Edge Event Activation (clk = 0) ---
        self.file.write(f"#{time_base + 5}\n")
        self.file.write(f"0{self.symbols['clk']}\n")

    def close(self):
        self.file.close()
