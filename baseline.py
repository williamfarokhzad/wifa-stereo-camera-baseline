"""Size the baseline of an ideal horizontal rectified stereo pair."""
import argparse
from dataclasses import dataclass, fields
from decimal import Decimal, localcontext
from fractions import Fraction as F
import json
from pathlib import Path


@dataclass(frozen=True)
class Design:
    focal_px: F
    near_mm: F
    far_mm: F
    error_px: F
    depth_budget_mm: F
    min_px: F
    max_px: F
    mounts_mm: tuple


def read_design(path):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f"duplicate field: {key}")
            obj[key] = value
        return obj

    data = json.loads(Path(path).read_text(encoding="utf-8"),
                      parse_float=F, parse_int=F, object_pairs_hook=unique)
    keys = {field.name for field in fields(Design)}
    if not isinstance(data, dict) or data.keys() != keys:
        raise ValueError("expected exactly: " + ", ".join(sorted(keys)))

    def number(value, name):
        if not isinstance(value, F) or not 0 <= value <= 10**9:
            raise ValueError(f"{name}: use a JSON number between 0 and 1000000000")
        return value

    mounts = data.pop("mounts_mm")
    if not isinstance(mounts, list) or not 1 <= len(mounts) <= 100:
        raise ValueError("mounts_mm: give 1 to 100 candidate positions")
    mounts = tuple(sorted(number(x, "mounts_mm") for x in mounts))
    d = Design(**{k: number(v, k) for k, v in data.items()}, mounts_mm=mounts)
    if d.near_mm <= 0 or d.far_mm < d.near_mm:
        raise ValueError("require 0 < near_mm <= far_mm")
    if min(d.focal_px, d.depth_budget_mm, d.min_px, *mounts) <= 0:
        raise ValueError("focal_px, depth_budget_mm, min_px and mounts must be positive")
    if d.max_px <= d.min_px:
        raise ValueError("max_px must exceed min_px")
    if len(set(mounts)) != len(mounts):
        raise ValueError("mounts_mm must not repeat a position")
    return d


def bounds(d):
    """Three independent limits; compare exact fractions before rounding."""
    lower_error = (d.error_px * d.far_mm * (d.far_mm + d.depth_budget_mm)
                   / (d.focal_px * d.depth_budget_mm))
    lower_min = d.far_mm * (d.min_px + d.error_px) / d.focal_px
    upper_max = d.near_mm * (d.max_px - d.error_px) / d.focal_px
    return lower_error, lower_min, upper_max


def audit_mount(d, baseline_mm):
    """Report measured disparity extremes and exact far depth error bound."""
    k = d.focal_px * baseline_mm
    far_low = k / d.far_mm - d.error_px
    near_high = k / d.near_mm + d.error_px
    worst = k / far_low - d.far_mm if far_low > 0 else None
    failures = tuple(label for fail, label in (
        (far_low < d.min_px, "below disparity floor"),
        (near_high > d.max_px, "above disparity ceiling"),
        (worst is None or worst > d.depth_budget_mm, "exceeds depth budget"),
    ) if fail)
    return far_low, near_high, worst, failures


def fmt(value):
    with localcontext() as ctx:
        ctx.prec = 40
        return f"{Decimal(value.numerator) / Decimal(value.denominator):.3f}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("design", help="path to a JSON design")
    args = parser.parse_args(argv)
    try:
        d = read_design(args.design)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    lower_error, lower_min, upper = bounds(d)
    lower = max(lower_error, lower_min)
    print(f"Limits (mm): error >= {fmt(lower_error)}; "
          f"disparity floor >= {fmt(lower_min)}; ceiling <= {fmt(upper)}")
    print(f"Continuous window (mm): [{fmt(lower)}, {fmt(upper)}]"
          if lower <= upper else "Continuous window: EMPTY")
    passes = 0
    for b in d.mounts_mm:
        far, near, error, failures = audit_mount(d, b)
        error_text = fmt(error) if error is not None else "unbounded"
        result = "; ".join(failures) if failures else "PASS"
        print(f"{fmt(b)} mm: far min {fmt(far)} px, near max {fmt(near)} px, "
              f"far error {error_text} mm | {result}")
        passes += not failures
    print(f"Candidate mounts passing: {passes}/{len(d.mounts_mm)}")
    return 0 if passes else 1


if __name__ == "__main__":
    raise SystemExit(main())
