#!/usr/bin/env python3
"""
dpll_solver.py
A recursive DPLL SAT checker that shares naming style with resolution_solver.py.
"""

import argparse
import time
import tracemalloc
import psutil
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional


# I/O helper (identical name to the Resolution script)
def parse_dimacs(path: Path) -> List[List[int]]:
    """Return a CNF formula as a list of lists of ints (each clause mutable)."""
    formula: List[List[int]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line or line[0] in {"c", "p"}:
                continue
            literals = list(map(int, line.strip().split()))
            if literals and literals[-1] == 0:
                literals.pop()
            if literals:
                formula.append(literals)
    return formula


# DPLL core
class DPLLSolver:
    """Classical Davis–Putnam–Logemann–Loveland search with unit and pure rules."""

    def __init__(self, cnf: List[List[int]]):
        self._formula = cnf
        self._stats = {"decisions": 0, "backtracks": 0, "unit": 0, "pure": 0}

    # helpers ---------------------------------------------------------------

    @staticmethod
    def _find_unit(clauses: List[List[int]]) -> Optional[int]:
        for clause in clauses:
            if len(clause) == 1:
                return clause[0]
        return None

    @staticmethod
    def _find_pure(clauses: List[List[int]]) -> Optional[int]:
        counter = {}
        for clause in clauses:
            for lit in clause:
                counter[lit] = counter.get(lit, 0) + 1
        for lit in counter:
            if -lit not in counter:
                return lit
        return None

    @staticmethod
    def _simplify(clauses: List[List[int]], lit: int) -> Optional[List[List[int]]]:
        new_formula: List[List[int]] = []
        for clause in clauses:
            if lit in clause:
                continue
            if -lit in clause:
                reduced = [x for x in clause if x != -lit]
                if not reduced:
                    return None
                new_formula.append(reduced)
            else:
                new_formula.append(clause[:])
        return new_formula

    def _propagate(self, clauses: List[List[int]], model: Dict[int, bool]):
        # unit propagation
        while True:
            unit = self._find_unit(clauses)
            if unit is None:
                break
            self._stats["unit"] += 1
            model[abs(unit)] = unit > 0
            clauses = self._simplify(clauses, unit)
            if clauses is None:
                return None, model

        # pure-literal elimination
        while True:
            pure = self._find_pure(clauses)
            if pure is None:
                break
            self._stats["pure"] += 1
            model[abs(pure)] = pure > 0
            clauses = [c for c in clauses if pure not in c]

        return clauses, model

    # public entry ----------------------------------------------------------

    def solve(self, clauses: Optional[List[List[int]]] = None,
              model: Optional[Dict[int, bool]] = None) -> Optional[Dict[int, bool]]:
        if clauses is None:
            clauses = [c[:] for c in self._formula]
        if model is None:
            model = {}

        clauses, model = self._propagate(clauses, model)
        if clauses is None:
            return None
        if not clauses:
            return model

        # choose a literal heuristically (first of first clause)
        pivot = clauses[0][0]
        self._stats["decisions"] += 1
        for truth in (True, False):
            next_model = model.copy()
            next_model[abs(pivot)] = truth
            reduced = self._simplify(clauses, pivot if truth else -pivot)
            if reduced is not None:
                result = self.solve(reduced, next_model)
                if result is not None:
                    return result
            self._stats["backtracks"] += 1
        return None

    # report helper
    def stats(self):
        return self._stats


# command-line driver (layout mirrors resolution_solver.py)
def main() -> None:
    cli = argparse.ArgumentParser(description="DPLL SAT checker")
    cli.add_argument("cnf", help="DIMACS CNF file")
    cli.add_argument("-v", "--verbose", action="store_true",
                     help="print satisfying assignment")
    args = cli.parse_args()

    clauses = parse_dimacs(Path(args.cnf))

    tracemalloc.start()
    proc = psutil.Process()
    mem_before = proc.memory_info().rss
    t0 = time.perf_counter()

    solver = DPLLSolver(clauses)
    model = solver.solve()

    t1 = time.perf_counter()
    mem_now, mem_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("\n==== DPLL Diagnostic ====")
    if model is None:
        print("s UNSATISFIABLE")
    else:
        print("s SATISFIABLE")
        if args.verbose:
            for var in sorted(model):
                print(f"v {var if model[var] else -var}")

    st = solver.stats()
    print(f"decisions = {st['decisions']}, backtracks = {st['backtracks']}, "
          f"unit_propagations = {st['unit']}, pure_literals = {st['pure']}")
    print(f"total steps = {sum(st.values())}")
    print(f"elapsed time = {t1 - t0:.4f} s")
    print(f"memory delta = {(proc.memory_info().rss - mem_before) / 1_048_576:.2f} MB")
    print(f"peak traced memory = {mem_peak / 1_048_576:.2f} MB")


if __name__ == "__main__":
    main()
