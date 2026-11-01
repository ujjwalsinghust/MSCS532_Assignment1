

import argparse
import csv
import gc
import hashlib
import json
import os
import platform
import random
import statistics
import sys
import time
import tracemalloc

from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar


T = TypeVar("T")
SEED = 20261101


# ------------------------------------------------------------
# MERGE SORT
# ------------------------------------------------------------

def merge_sort(values: list[T]) -> None:
    """Sort the list using stable merge sort and one reusable buffer."""
    if len(values) < 2:
        return

    buffer = values.copy()
    _merge_sort_range(values, buffer, 0, len(values))


def _merge_sort_range(
    values: list[T],
    buffer: list[T],
    lo: int,
    hi: int
) -> None:
    """Sort the interval starting at lo and ending before hi."""
    if hi - lo <= 1:
        return

    # Divide the interval into two halves.
    mid = (lo + hi) // 2

    # Recursively sort both halves.
    _merge_sort_range(values, buffer, lo, mid)
    _merge_sort_range(values, buffer, mid, hi)

    left = lo
    right = mid
    output = lo

    # Merge the sorted halves into the shared buffer.
    while left < mid and right < hi:
        # Choosing the left item on ties preserves stability.
        if values[left] <= values[right]:
            buffer[output] = values[left]
            left += 1
        else:
            buffer[output] = values[right]
            right += 1

        output += 1

    # Copy any remaining items from the left half.
    while left < mid:
        buffer[output] = values[left]
        left += 1
        output += 1

    # Copy any remaining items from the right half.
    while right < hi:
        buffer[output] = values[right]
        right += 1
        output += 1

    # Copy the merged interval back without creating a slice.
    for index in range(lo, hi):
        values[index] = buffer[index]


# ------------------------------------------------------------
# QUICKSORT
# ------------------------------------------------------------

def quick_sort(values: list[T]) -> None:
    """
    Sort the list using the final element as the pivot.

    Recursing only on the smaller partition limits stack depth
    to O(log n). Worst-case running time remains O(n squared).
    """
    _quick_sort_range(values, 0, len(values) - 1)


def _partition(values: list[T], lo: int, hi: int) -> int:
    """Partition the interval using the Lomuto partition scheme."""
    pivot = values[hi]
    boundary = lo

    for scan in range(lo, hi):
        if values[scan] <= pivot:
            values[boundary], values[scan] = (
                values[scan],
                values[boundary],
            )
            boundary += 1

    # Place the pivot in its final sorted position.
    values[boundary], values[hi] = values[hi], values[boundary]

    return boundary


def _quick_sort_range(values: list[T], lo: int, hi: int) -> None:
    while lo < hi:
        pivot_index = _partition(values, lo, hi)

        # Recurse on the smaller partition and loop over the larger one.
        if pivot_index - lo < hi - pivot_index:
            _quick_sort_range(values, lo, pivot_index - 1)
            lo = pivot_index + 1
        else:
            _quick_sort_range(values, pivot_index + 1, hi)
            hi = pivot_index - 1


ALGORITHMS = {
    "Merge sort": merge_sort,
    "Quicksort": quick_sort,
}


# ------------------------------------------------------------
# CORRECTNESS CHECKS AND DATASETS
# ------------------------------------------------------------

def run_correctness_checks():
    """Check edge cases and random inputs before benchmarking."""
    generator = random.Random(SEED)

    cases = [
        [],
        [1],
        [3, 1, 2],
        [5] * 25,
        [0, -2, 8, -2, 3],
        list(range(100)),
        list(range(99, -1, -1)),
    ]

    for size in (10, 63, 128, 257):
        cases.append([
            generator.randrange(-100, 101)
            for _ in range(size)
        ])

    for sorter in ALGORITHMS.values():
        for original in cases:
            actual = original.copy()
            sorter(actual)

            # Built-in sorting is used only to verify correctness.
            if actual != sorted(original):
                raise AssertionError(
                    f"Correctness failure in {sorter.__name__}"
                )

    print("Correctness checks passed for both algorithms.", flush=True)


def datasets(size):
    """Generate identical datasets for both sorting algorithms."""
    ascending = list(range(size))

    shuffled = ascending.copy()
    random.Random(SEED + size).shuffle(shuffled)

    return {
        "Sorted": ascending,
        "Reverse sorted": list(reversed(ascending)),
        "Random": shuffled,
    }


# ------------------------------------------------------------
# PERFORMANCE MEASUREMENT
# ------------------------------------------------------------

def measure_time(sorter, template, expected):
    """Measure sorting time without memory tracing."""
    values = template.copy()

    # Input copying and garbage collection are outside the timer.
    gc.collect()
    was_enabled = gc.isenabled()
    gc.disable()

    try:
        start = time.perf_counter_ns()
        sorter(values)
        elapsed = time.perf_counter_ns() - start
    finally:
        if was_enabled:
            gc.enable()

    # Correctness validation is outside the timer.
    if values != expected:
        raise AssertionError(
            f"{sorter.__name__} returned an incorrect ordering"
        )

    return elapsed


def measure_memory(sorter, template, expected):
    """
    Measure peak newly traced Python allocations during sorting.

    The existing input list and input objects are excluded.
    This metric is not total process memory.
    """
    values = template.copy()

    gc.collect()
    was_enabled = gc.isenabled()
    gc.disable()

    tracemalloc.start()

    try:
        sorter(values)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

        if was_enabled:
            gc.enable()

    if values != expected:
        raise AssertionError(
            f"{sorter.__name__} returned an incorrect ordering"
        )

    return peak


def cpu_model():
    """Return processor information when the operating system exposes it."""
    source = Path("/proc/cpuinfo")

    if source.exists():
        for line in source.read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()

    return platform.processor() or "Not exposed by runtime"


def save_csv(path, rows):
    """Write recorded measurements to a CSV file."""
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(rows[0]),
        )
        writer.writeheader()
        writer.writerows(rows)


# ------------------------------------------------------------
# GRAPH GENERATION
# ------------------------------------------------------------

def create_graphs(output):
    """Create graphs after all measurements are complete."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\nCSV results were saved, but matplotlib is missing.")
        print("Install it using:")
        print(f'"{sys.executable}" -m pip install matplotlib')
        print("Then run this script again to generate graphs.")
        return

    colors = {
        "Merge sort": "#305B8E",
        "Quicksort": "#B45426",
    }

    distributions = ("Sorted", "Reverse sorted", "Random")

    with (output / "summary.csv").open() as stream:
        rows = list(csv.DictReader(stream))

    sizes = sorted({int(row["n"]) for row in rows})

    lookup = {
        (row["dataset"], int(row["n"]), row["algorithm"]): row
        for row in rows
    }

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
    })

    # Compare the algorithms at the largest input size.
    fig, axes = plt.subplots(
        1, 2,
        figsize=(8, 3.25),
        layout="constrained",
    )

    metrics = (
        ("median_ms", "Median runtime (ms)"),
        ("median_peak_kib", "Peak traced allocation (KiB)"),
    )

    positions = [0, 1, 2]
    largest_size = sizes[-1]

    for panel, (metric, label) in enumerate(metrics):
        ax = axes[panel]

        for offset, (name, color) in zip(
            (-0.19, 0.19),
            colors.items(),
        ):
            values = [
                float(lookup[(dataset, largest_size, name)][metric])
                for dataset in distributions
            ]

            bars = ax.bar(
                [position + offset for position in positions],
                values,
                width=0.35,
                color=color,
                label=name,
            )

            for bar, value in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    value * 1.12,
                    f"{value:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

        all_values = [
            float(lookup[(dataset, largest_size, name)][metric])
            for dataset in distributions
            for name in colors
        ]

        if min(all_values) > 0:
            ax.set_yscale("log")
            ax.set_ylim(
                min(all_values) / 1.8,
                max(all_values) * 5,
            )
        else:
            ax.set_ylim(0, max(all_values) * 1.5 + 0.001)

        ax.set_xticks(
            positions,
            ("Sorted", "Reverse", "Random"),
        )
        ax.set_ylabel(label)
        ax.grid(axis="y", alpha=0.18)
        ax.set_axisbelow(True)

    axes[0].set_title(f"Runtime at n = {largest_size:,}")
    axes[1].set_title(f"Extra allocations at n = {largest_size:,}")
    axes[0].legend(frameon=False, loc="upper right", fontsize=8)

    fig.savefig(output / "comparison.png", dpi=300)
    fig.savefig(output / "comparison.svg")
    plt.close(fig)

    # Show how performance changes as input size increases.
    fig, axes = plt.subplots(
        2, 3,
        figsize=(10.5, 6.2),
        layout="constrained",
    )

    for column, distribution in enumerate(distributions):
        for row_index, (metric, label) in enumerate(metrics):
            ax = axes[row_index, column]

            for name, color in colors.items():
                values = [
                    float(lookup[(distribution, size, name)][metric])
                    for size in sizes
                ]

                ax.plot(
                    sizes,
                    values,
                    color=color,
                    marker="o",
                    label=name,
                    linewidth=1.8,
                )

            ax.set_xscale("log", base=2)

            if all(
                float(lookup[(distribution, size, name)][metric]) > 0
                for size in sizes
                for name in colors
            ):
                ax.set_yscale("log")

            ax.set_xticks(
                sizes,
                [f"{size:,}" for size in sizes],
            )
            ax.set_xlabel("Input size")
            ax.grid(alpha=0.2)

            if column == 0:
                ax.set_ylabel(label)

            if row_index == 0:
                ax.set_title(distribution)

    axes[0, 0].legend(frameon=False, fontsize=9)

    fig.savefig(output / "scaling.png", dpi=300)
    fig.savefig(output / "scaling.svg")
    plt.close(fig)


# ------------------------------------------------------------
# MAIN EXPERIMENT
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[500, 1000, 2000],
    )
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--memory-repeats", type=int, default=3)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "results",
    )

    args = parser.parse_args()

    if (
        min(args.sizes) < 2
        or args.repeats < 1
        or args.memory_repeats < 1
    ):
        parser.error(
            "Sizes must be at least 2 and repeat counts must be positive."
        )

    args.output.mkdir(parents=True, exist_ok=True)

    run_correctness_checks()
    print(
        "Running benchmarks. Ordered quicksort inputs take longer.",
        flush=True,
    )

    raw_measurements = []
    summaries = []

    for size in args.sizes:
        expected = list(range(size))

        for distribution, template in datasets(size).items():
            timing = {name: [] for name in ALGORITHMS}
            memory = {name: [] for name in ALGORITHMS}

            # Warm up both algorithms before collecting results.
            for sorter in ALGORITHMS.values():
                warmup = template.copy()
                sorter(warmup)

                if warmup != expected:
                    raise AssertionError("Warm-up correctness check failed.")

            # Alternate execution order between timing trials.
            for trial in range(args.repeats):
                names = list(ALGORITHMS)

                if trial % 2:
                    names.reverse()

                for name in names:
                    elapsed = measure_time(
                        ALGORITHMS[name],
                        template,
                        expected,
                    )

                    timing[name].append(elapsed)

                    raw_measurements.append({
                        "dataset": distribution,
                        "n": size,
                        "algorithm": name,
                        "metric": "runtime_ns",
                        "trial": trial + 1,
                        "value": elapsed,
                    })

            # Measure memory separately to avoid distorting timing.
            for trial in range(args.memory_repeats):
                for name, sorter in ALGORITHMS.items():
                    peak = measure_memory(
                        sorter,
                        template,
                        expected,
                    )

                    memory[name].append(peak)

                    raw_measurements.append({
                        "dataset": distribution,
                        "n": size,
                        "algorithm": name,
                        "metric": "peak_bytes",
                        "trial": trial + 1,
                        "value": peak,
                    })

            for name in ALGORITHMS:
                sample = timing[name]

                row = {
                    "dataset": distribution,
                    "n": size,
                    "algorithm": name,
                    "median_ms": statistics.median(sample) / 1_000_000,
                    "min_ms": min(sample) / 1_000_000,
                    "max_ms": max(sample) / 1_000_000,
                    "median_peak_kib": (
                        statistics.median(memory[name]) / 1024
                    ),
                    "time_repeats": args.repeats,
                    "memory_repeats": args.memory_repeats,
                }

                summaries.append(row)

                print(
                    f"{distribution:14} "
                    f"n={size:5} "
                    f"{name:10} "
                    f"{row['median_ms']:9.3f} ms "
                    f"{row['median_peak_kib']:7.3f} KiB",
                    flush=True,
                )

            # Save completed measurements after each dataset.
            save_csv(
                args.output / "summary.csv",
                summaries,
            )
            save_csv(
                args.output / "raw_measurements.csv",
                raw_measurements,
            )

    source_path = Path(__file__).resolve()

    metadata = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "course": "Algorithms and Data Structures",
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_model": cpu_model(),
        "logical_cpus_visible": os.cpu_count(),
        "sizes": args.sizes,
        "seed": SEED,
        "randomization": (
            "One shuffled distinct-integer permutation per size, seed + n"
        ),
        "timing_repeats": args.repeats,
        "memory_repeats": args.memory_repeats,
        "timer": "time.perf_counter_ns",
        "memory": (
            "Median peak newly traced Python allocations during sorting"
        ),
        "excluded": [
            "input generation",
            "input copy",
            "validation",
            "pre-existing input objects",
        ],
        "limitations": (
            "Traced allocations are not total process memory or complete "
            "native stack memory. Memory tracing is disabled during timing."
        ),
        "source_sha256": {
            source_path.name: hashlib.sha256(python -u sorting.py
                source_path.read_bytes()
            ).hexdigest()
        },
    }

    (args.output / "environment.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )

    create_graphs(args.output)

    print(f"\nResults saved in: {args.output.resolve()}")


if __name__ == "__main__":
    main()