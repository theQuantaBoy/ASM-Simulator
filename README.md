# ASM-Simulator

A cycle-accurate simulator for synchronous digital systems described as Algorithmic State Machines (ASMs). Given an ASM description and a testbench, it simulates the design clock-by-clock and prints a signal table. Optionally generates a VCD waveform file for inspection in GTKWave.

Originally developed as part of the Digital Systems Design (DSD) course midterm exam, Spring 2026, at Sharif University of Technology (Dr. Ejlali).

---

## Features

- Accepts ASM descriptions as plain text (`.txt`) or JSON (`.json`)
- Supports STATE, CONDITIONAL, and DECISION boxes
- Testbench-driven input stimulus via JSON
- Adaptive early-exit or fixed cycle count simulation modes
- VCD waveform output compatible with GTKWave

---

## Project Structure

```
ASM-Simulator/
├── src/
│   ├── main.py          # Entry point and simulation loop
│   ├── loader.py        # ASM text/JSON parser and model builder
│   ├── evaluator.py     # Expression and micro-instruction evaluator
│   ├── asm_boxes.py     # STATE, CONDITIONAL, DECISION box classes
│   ├── datapath.py      # Register and Datapath models
│   ├── instructions.py  # MicroInstruction and Condition wrappers
│   └── vcd_logger.py    # VCD waveform file writer
└── data/
    ├── divider/
    │   ├── divider.txt
    │   ├── divider.json
    │   └── tb_*.json
    └── multiplier/
        ├── multiplier.json
        └── tb_*.json
```

---

## Usage

```bash
python src/main.py <asm_file> <testbench_file> [options]
```

| Option | Description |
|---|---|
| `-a`, `--all` | Show all signals, not just declared outputs |
| `-t N`, `--timeout N` | Run for exactly N cycles |
| `--vcd [filename]` | Write a VCD file (default: `waves.vcd`) next to the ASM file |

---

## Example

**ASM description** (`data/divider/divider.txt`) — integer division with remainder:

```
INPUT in1<31,0>, in2<31,0>;
REGISTER A<31:0>, B<31:0>, Q<31:0>, R<31:0>;
REGISTER End<0,0>, Err<0,0>, S<0,0>;
OUTPUT Q, R, End, Err;
INITIAL Box1;

Box1: STATE, {}, Box2;
Box2: DECISION, {S}, 0:Box1, 1:Box3;
Box3: CONDITIONAL, {A=in1, B=in2, Q=0, End=0}, Box4;
Box4: STATE, {}, Box5;
Box5: DECISION, {|B}, 0:Box6, 1:Box7;
Box6: CONDITIONAL, {Err=1, End=1}, Box1;
Box7: CONDITIONAL, {Err=0}, Box8;
Box8: STATE, {}, Box9;
Box9: DECISION, {B>A}, 0:Box10, 1:Box11;
Box10: CONDITIONAL, {A=A-B, Q=Q+1}, Box8;
Box11: CONDITIONAL, {R=A, End=1}, Box1;
```

**Testbench** (`data/divider/tb_exact.json`) — compute 15 ÷ 3:

```json
{
    "total_cycles": 12,
    "time_line": {
        "1": {"in1": 15, "in2": 3},
        "2": {"S": 1},
        "3": {"S": 0}
    }
}
```

**Run:**

```bash
python src/main.py data/divider/divider.txt data/divider/tb_exact.json
```

**Output:**

| Clock Cycle | Active State | Q | R | End | Err |
|---|---|---|---|---|---|
| 0 | Box1 | 0 | 0 | 0 | 0 |
| 1 | Box1 | 0 | 0 | 0 | 0 |
| 2 | Box1 | 0 | 0 | 0 | 0 |
| 3 | Box4 | 0 | 0 | 0 | 0 |
| 4 | Box8 | 0 | 0 | 0 | 0 |
| 5 | Box8 | 1 | 0 | 0 | 0 |
| 6 | Box8 | 2 | 0 | 0 | 0 |
| 7 | Box8 | 3 | 0 | 0 | 0 |
| 8 | Box8 | 4 | 0 | 0 | 0 |
| 9 | Box8 | 5 | 0 | 0 | 0 |
| 10 | Box1 | 5 | 0 | 1 | 0 |
| 11 | Box1 | 5 | 0 | 1 | 0 |

Result: Q=5, R=0 ✓

---

## Testbench Format

The `time_line` object maps cycle numbers to signal overrides applied at the start of that cycle. Any input or register can be driven this way. `total_cycles` fixes the simulation length; omitting it enables adaptive mode, where the simulator stops automatically once the design returns to its initial state.

---

## Requirements

Python 3.10+ (no external dependencies).