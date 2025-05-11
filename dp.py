#!/usr/bin/env python3
"""
dp_solver.py
Davis–Putnam elimination SAT checker that works on a single DIMACS CNF
instance exactly like dpll_solver.py and resolution_solver.py.
"""

import argparse
import time
import tracemalloc
import psutil

# CNF reader  (shared with the other solvers)
def parse_dimacs(path):
    """Return a CNF formula as a list of mutable lists of ints."""
    cnf = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line[0] in {"c", "p"}:
                continue
            lits = list(map(int, line.split()))
            if lits:
                cnf.append(lits[:-1])          # drop trailing 0
    return cnf


# Davis–Putnam elimination
class DPSolver:
    def __init__(self, clauses):
        self._clauses = [c[:] for c in clauses]
        self._stats = {"vars_eliminated": 0, "resolvents": 0}

    #helper
    @staticmethod
    def _choose_var(clauses):
        for clause in clauses:
            if clause:
                return abs(clause[0])
        return None

    def _eliminate(self, var):
        pos, neg, rest = [], [], []
        for clause in self._clauses:
            if var in clause:
                pos.append(clause)
            elif -var in clause:
                neg.append(clause)
            else:
                rest.append(clause)

        new_clauses = []
        for c1 in pos:
            for c2 in neg:
                resolvent = [l for l in (set(c1) | set(c2)) if l not in {var, -var}]
                if not resolvent:          # empty resolvent ⇒ UNSAT
                    return None
                new_clauses.append(resolvent)
                self._stats["resolvents"] += 1

        self._clauses = rest + new_clauses
        self._stats["vars_eliminated"] += 1
        return self._clauses

    #public entry
    def solve(self):
        while True:
            if not self._clauses:
                return True               # all clauses satisfied → SAT
            if any(len(c) == 0 for c in self._clauses):
                return False              # empty clause found → UNSAT

            v = self._choose_var(self._clauses)
            if v is None:                 # no variable left
                return True
            if self._eliminate(v) is None:
                return False


# CLI wrapper
def main():
    cli = argparse.ArgumentParser(description="DP SAT checker")
    cli.add_argument("cnf", help="DIMACS CNF input file")
    args = cli.parse_args()

    clauses = parse_dimacs(args.cnf)

    tracemalloc.start()
    proc = psutil.Process()
    mem_before = proc.memory_info().rss
    t0 = time.perf_counter()

    solver = DPSolver(clauses)
    sat = solver.solve()

    t1 = time.perf_counter()
    _, mem_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("\n==== DP Diagnostic ====")
    print(f"Result: {'SATISFIABLE' if sat else 'UNSATISFIABLE'}")
    print(f"Original clauses: {len(clauses)}")
    print(f"Clauses after elimination: {len(solver._clauses)}")
    st = solver._stats
    print(f"Variables eliminated: {st['vars_eliminated']}")
    print(f"Resolvents generated: {st['resolvents']}")
    print(f"Elapsed time: {t1 - t0:.4f} s")
    print(f"Memory delta: {(proc.memory_info().rss - mem_before) / 1_048_576:.2f} MB")
    print(f"Peak traced memory: {mem_peak / 1_048_576:.2f} MB")


if __name__ == "__main__":
    main()
