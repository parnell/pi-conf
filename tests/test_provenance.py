import os
import sys
import tempfile
import unittest

import pi_conf.config as config
from pi_conf import Config

basedir = os.path.abspath(os.getcwd())
sys.path.append(basedir)


class TestProvenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def test_provenance(self):
        cfg = Config.from_dict({"a": 1})
        self.assertEqual(cfg.provenance[-1].source, "dict")
        self.assertEqual(len(cfg.provenance), 1)

    def test_provenance2(self):
        cfg = Config.from_dict({"a": 1})
        self.assertEqual(cfg.provenance[-1].source, "dict")
        cfg.update({"b": 2})
        self.assertEqual(cfg.provenance[-1].source, "dict")
        self.assertEqual(len(cfg.provenance), 2)

    def test_provenance_from_set_config(self):
        s = """
        [a]
        b = 1"""
        ### Create a random tempoary file and write the string to it
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml") as f:
            f.write(s)
            f.flush()

            cfg = config.set_config(f.name)

            self.assertEqual(len(cfg.provenance), 1)
            self.assertEqual(cfg.provenance[0].source, f.name)

    def test_provenance_from_load_config(self):
        s = """
        [a]
        b = 1"""
        ### Create a random tempoary file and write the string to it
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml") as f:
            f.write(s)
            f.flush()

            cfg = config.load_config(f.name)

            self.assertEqual(len(cfg.provenance), 1)
            self.assertEqual(cfg.provenance[0].source, f.name)


if __name__ == "__main__":
    unittest.main()
