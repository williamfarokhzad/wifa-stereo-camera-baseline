from fractions import Fraction as F
from pathlib import Path
from random import Random
from subprocess import run
import sys
from tempfile import TemporaryDirectory
import unittest

from baseline import Design, audit_mount, bounds, read_design

ROOT = Path(__file__).resolve().parents[1]


class BaselineTests(unittest.TestCase):
    def design(self, name):
        return read_design(ROOT / "examples" / f"{name}.json")

    def test_hand_calculated_bounds(self):
        self.assertEqual(bounds(self.design("narrow-window")),
                         (F("94.6875"), F("8.4375"), F("99.84375")))

    def test_inclusive_lower_and_upper(self):
        d = self.design("narrow-window")
        lo, _, hi = bounds(d)
        self.assertEqual(audit_mount(d, lo)[2:], (F(30), ()))
        self.assertEqual(audit_mount(d, hi)[1], F(160))
        self.assertEqual(audit_mount(d, hi)[3], ())
        self.assertIn("exceeds depth budget", audit_mount(d, lo - F(1, 100000))[3])
        self.assertIn("above disparity ceiling", audit_mount(d, hi + F(1, 100000))[3])

    def test_each_constraint_can_reject_a_mount(self):
        d = self.design("disparity-floor")
        self.assertEqual(audit_mount(d, F(85))[3], ("below disparity floor",))
        self.assertEqual(audit_mount(self.design("narrow-window"), F(80))[3],
                         ("exceeds depth budget",))
        self.assertEqual(audit_mount(self.design("narrow-window"), F(100))[3],
                         ("above disparity ceiling",))

    def test_unbounded_far_error(self):
        d = Design(F(100), F(500), F(1000), F(1), F(100), F(2), F(100), (F(10),))
        self.assertIsNone(audit_mount(d, F(10))[2])
        self.assertIn("exceeds depth budget", audit_mount(d, F(10))[3])

    def test_zero_uncertainty(self):
        d = Design(F(400), F(200), F(600), F(0), F(1), F(5), F(50), (F(20),))
        self.assertEqual(bounds(d), (0, F("7.5"), 25))
        self.assertEqual(audit_mount(d, F(20))[2:], (F(0), ()))

    def test_one_point_range_and_single_feasible_mount(self):
        d = Design(F(500), F(500), F(500), F(1), F(250), F(2), F(4), (F(3),))
        lo_error, lo_min, hi = bounds(d)
        self.assertEqual((max(lo_error, lo_min), hi), (3, 3))
        self.assertEqual(audit_mount(d, F(3))[3], ())

    def test_direct_projection_oracle(self):
        # Independently project a scene point into each of two cameras.
        # Test both signed errors at three depths, not the bound algebra.
        rng = Random(342)
        passes = 0
        for _ in range(600):
            f = F(rng.randrange(350, 1200))
            near = F(rng.randrange(200, 950))
            far = near + rng.randrange(20, 3500)
            error = F(rng.randrange(0, 9), 8)
            budget = F(rng.randrange(2, 150))
            b = F(rng.randrange(20, 220))
            d = Design(f, near, far, error, budget, F(4), F(160), (b,))
            good = True
            for z in (near, (near + far) / 2, far):
                x = F(rng.randrange(-150, 151))
                left = 320 + f * x / z
                right = 320 + f * (x - b) / z
                for perturb in (-error, error):
                    observed = left - right + perturb
                    good &= (d.min_px <= observed <= d.max_px and
                             abs(f * b / observed - z) <= budget)
            lo_error, lo_min, hi = bounds(d)
            self.assertEqual(max(lo_error, lo_min) <= b <= hi, good)
            self.assertEqual(not audit_mount(d, b)[3], good)
            passes += good
        self.assertGreater(passes, 0)
        self.assertLess(passes, 600)

    def test_cli_outputs_and_exit_codes(self):
        for example, count, code in (("narrow-window", "1/3", 0),
                                     ("no-window", "0/3", 1),
                                     ("no-mount", "0/2", 1),
                                     ("disparity-floor", "1/2", 0)):
            with self.subTest(example=example):
                p = run([sys.executable, "baseline.py", f"examples/{example}.json"],
                        cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(p.returncode, code, p.stderr)
                self.assertIn("Candidate mounts passing: " + count, p.stdout)
                self.assertEqual("EMPTY" in p.stdout, example == "no-window")

    def test_invalid_inputs(self):
        base = (ROOT / "examples/narrow-window.json").read_text()
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            for wrong in (base.replace("0.25", "NaN"), base.replace("0.25", "true"),
                          base.replace("800", '"800"'), base.replace("500", "4000"),
                          base.replace("80,96,100", "80,80"),
                          base.replace('"focal_px":800', '"focal_px":800,"focal_px":800')):
                p.write_text(wrong)
                with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                    read_design(p)


if __name__ == "__main__":
    unittest.main()
