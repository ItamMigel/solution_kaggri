import tempfile
import unittest
from pathlib import Path

from lab.hplus import route_land


class RouteLandTest(unittest.TestCase):
    def test_normalise(self):
        self.assertEqual(route_land.normalise(None), route_land.DEFAULT)
        with self.assertRaises(ValueError):
            route_land.normalise({"rl_expert": "V39"})
        with self.assertRaises(ValueError):
            route_land.normalise({"extra": True})
        with self.assertRaises(ValueError):
            route_land.normalise({"rl_land_k": 24})

    def test_build_compiles(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "base.py"; out = Path(td) / "out.py"
            # The parent symbols are supplied only at runtime by modules.build;
            # compiling verifies the generated agent remains self-contained.
            base.write_text("def agent(obs, config=None):\n    return {'market': []}\n")
            info = route_land.build(base, {"rl_on": True}, out)
            self.assertTrue(out.exists())
            self.assertFalse(info["default_off"])

    def _call(self, expert, quadrants, *, pending=None, owed=0):
        ns = {"agent": lambda obs, config=None: {"market": [["SELL", "WHEAT", 1]]}}
        class Chassis: pass
        chassis = Chassis(); chassis.players = {0: {"router_state": {"expert": expert}}}
        class Impl: pass
        impl = Impl(); impl.chassis = chassis
        ns["_IMPL"] = impl
        ns["_HP_LAND"] = {0: {"pending": pending, "owed": owed}}
        ns["_HP"] = {"land_k": 24, "land_buffer": 300}
        called = []
        def hp(obs, action): called.append(True); return {"market": [["BUY_LAND"]]}
        ns["_hp_land"] = hp
        exec(route_land.MODULE_SRC.replace("__RL_GENES__", repr({"rl_on": True, "rl_expert": "EXP240", "rl_land_k": 48, "rl_buffer": 300})), ns)
        obs = {"player": 0, "farms": [{"unlocked_quadrants": ["NW"] * quadrants}]}
        return ns["agent"](obs), called

    def test_only_exp240_second_land_or_reconciliation(self):
        self.assertEqual(self._call("EXP240", 2)[1], [True])
        self.assertEqual(self._call("V39", 2)[1], [])
        self.assertEqual(self._call("EXP240", 3)[1], [])
        self.assertEqual(self._call("EXP240", 3, pending=2)[1], [True])


if __name__ == "__main__":
    unittest.main()
