from pathlib import Path
from ncmemsim.benchmark import write_benchmark_report

if __name__ == "__main__":
    path = write_benchmark_report(Path("validation/benchmark_results.json"), repeats=3)
    print(path)
