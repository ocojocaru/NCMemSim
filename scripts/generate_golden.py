from pathlib import Path
from ncmemsim.golden import write_golden_suite

if __name__ == "__main__":
    path = write_golden_suite(Path("validation/golden_reference/phase_d6_v0.9.0.json"))
    print(path)
