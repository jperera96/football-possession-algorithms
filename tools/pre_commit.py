"""Pre-commit verification script.

Runs code quality checks, strategy unit tests, and submission validation.
Cross-platform: runs seamlessly on Windows (PowerShell/CMD), Linux, and macOS.

Usage:
    python tools/pre_commit.py
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def run_check(name, cmd):
    print(f"--> [Checking] {name}...")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAILED: {name}")
        print(result.stdout)
        print(result.stderr)
        return False
    print(f"    [PASSED] {name}")
    return True


def main():
    print("=" * 60)
    print("Running Pre-Commit Verification Suite")
    print("=" * 60)

    python_bin = sys.executable

    checks = [
        ("Strategy Synthetic Unit Tests", [python_bin, "run_experiment.py", "--test-all"]),
        ("Baseline Submission Contract", [python_bin, "evaluation/validate_submission.py", "evaluation/results/baseline_smooth50.csv"]),
        ("Baseline Public GT Scoring", [python_bin, "evaluation/run_evaluation.py"]),
    ]

    all_passed = True
    for name, cmd in checks:
        if not run_check(name, cmd):
            all_passed = False
            break

    print("=" * 60)
    if all_passed:
        print("ALL PRE-COMMIT CHECKS PASSED! Ready to commit.")
        sys.exit(0)
    else:
        print("PRE-COMMIT CHECKS FAILED! Please fix the errors above before committing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
