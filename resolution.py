#!/usr/bin/env python3
"""
resolution_solver_renamed.py
Same logic as the original ClauseReasoner version, but all identifiers
have new names.  No new imports added.
"""

import argparse
import time
import tracemalloc
import psutil


#CNF reader
def load_dimacs(file_path):
    """Read a DIMACS CNF file and return a list of frozenset clauses."""
    clauses = []
    with open(file_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line[0] in {"c", "p"}:
                continue
            numbers = list(map(int, line.split()))
            clauses.append(frozenset(numbers[:-1]))  # drop trailing 0
    return clauses


#Resolution engine
class ResolutionEngine:
    def __init__(self, clauses_input):
        self.clauses_initial = list(clauses_input)
        self.clauses_seen = set(clauses_input)
        self.derived_indices = []
        self.stats = {"pairs": 0}

    def _resolve_pair(self, left, right):
        resolvents = []
        for lit in left:
            if -lit in right:
                combined = (left - {lit}) | (right - {-lit})
                resolvents.append(frozenset(combined))
        return resolvents

    def solve(self):
        pool = self.clauses_initial[:]
        total_count = len(pool)

        while True:
            current_len = len(pool)
            for i in range(current_len):
                for j in range(i + 1, current_len):
                    for clause in self._resolve_pair(pool[i], pool[j]):
                        self.stats["pairs"] += 1
                        if clause not in self.clauses_seen:
                            total_count += 1
                            pool.append(clause)
                            self.clauses_seen.add(clause)
                            self.derived_indices.append(total_count)
                            if not clause:
                                return True  # empty clause -> UNSAT
            # no growth in this iteration -> fixed point, SAT
            if len(pool) == len(self.clauses_initial) + len(self.derived_indices) == total_count:
                return False


#CLI wrapper
def main():
    parser = argparse.ArgumentParser(description="Resolution SAT analyzer")
    parser.add_argument("file", help="Input CNF file in DIMACS format")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Display indices of derived clauses")
    args = parser.parse_args()

    formula = load_dimacs(args.file)

    tracemalloc.start()
    process = psutil.Process()
    mem_before = process.memory_info().rss
    t0 = time.perf_counter()

    solver = ResolutionEngine(formula)
    is_unsat = solver.solve()

    t1 = time.perf_counter()
    _, mem_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("\n==== Resolution Diagnostic ====")
    print(f"Outcome: {'UNSATISFIABLE' if is_unsat else 'SATISFIABLE'}")
    print(f"Initial clause count: {len(formula)}")
    print(f"Final clause count: {len(solver.clauses_seen)}")
    if args.verbose:
        print("Derived clause indices:", ", ".join(map(str, solver.derived_indices)))
    print(f"Resolution attempts: {solver.stats['pairs']}")
    print(f"Elapsed time: {t1 - t0:.4f} seconds")
    print(f"Memory change: {(process.memory_info().rss - mem_before) / (1024 ** 2):.2f} MB")
    print(f"Peak memory usage: {mem_peak / (1024 ** 2):.2f} MB")


if __name__ == "__main__":
    main()
