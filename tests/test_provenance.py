import os
import sys
import tempfile
import unittest

import pi_conf.config as config
from pi_conf import Config
from pi_conf.provenance import ProvenanceOp

basedir = os.path.abspath(os.getcwd())
sys.path.append(basedir)


class TestProvenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def test_provenance_of_config_provenance_disabled(self):
        from pi_conf.provenance import _provenance_manager

        cfg = Config({"a": 1}, enable_provenance=False)

        self.assertEqual(len(cfg.provenance), 0)
        oid = id(cfg)
        self.assertTrue(oid not in _provenance_manager._enabled)

    def test_provenance_from_dict_directly(self):
        cfg = Config({"a": 1})
        self.assertEqual(cfg.provenance[-1].source, "dict")
        self.assertEqual(cfg.provenance[-1].operation, ProvenanceOp.set)
        self.assertEqual(len(cfg.provenance), 1)

    def test_provenance_from_dict(self):
        cfg = Config.from_dict({"a": 1})
        self.assertEqual(cfg.provenance[-1].source, "dict")
        self.assertEqual(cfg.provenance[-1].operation, ProvenanceOp.set)
        self.assertEqual(len(cfg.provenance), 1)

    def test_proventest_provenance_from_dict2(self):
        cfg = Config.from_dict({"a": 1})
        self.assertEqual(cfg.provenance[-1].source, "dict")
        self.assertEqual(cfg.provenance[-1].operation, ProvenanceOp.set)
        cfg.update({"b": 2})
        self.assertEqual(cfg.provenance[-1].source, "dict")
        self.assertEqual(cfg.provenance[-1].operation, ProvenanceOp.update)

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
            self.assertEqual(cfg.provenance[0].operation, ProvenanceOp.set)

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
    testmethod = ""
    if testmethod:
        suite = unittest.TestSuite()
        suite.addTest(TestProvenance(testmethod))
        unittest.TextTestRunner().run(suite)
    else:
        unittest.main()
