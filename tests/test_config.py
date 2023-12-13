import os
import sys
import tempfile
import unittest

from pi_conf.config import _load_config_file

basedir = os.path.abspath(os.getcwd())
sys.path.append(basedir)


class TestConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def test_config_empty_at_start(self):
        from pi_conf import cfg

        self.assertEqual(len(cfg), 0)

    def test_config_attr_dict(self):
        from pi_conf import Config

        cfg = Config.make_attr_dict({})
        cfg.update({"a": 1})

        self.assertEqual(cfg.a, 1)

    def test_config_loads_toml(self):
        s = """
        [a]
        b = 1"""
        ### Create a random tempoary file and write the string to it
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml") as f:
            f.write(s)
            f.flush()

            cfg = _load_config_file(f.name)
            self.assertEqual(cfg["a"]["b"], 1)

    def test_config_loads_json(self):
        s = """
        {
            "a": {
                "b": 1
            }
        }
        """
        ### Create a random tempoary file and write the string to it
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as f:
            f.write(s)
            f.flush()

            cfg = _load_config_file(f.name)
            self.assertEqual(cfg["a"]["b"], 1)

    def test_config_loads_yaml(self):
        s = """
        a:
            b: 1
        """
        ### Create a random tempoary file and write the string to it
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as f:
            f.write(s)
            f.flush()

            cfg = _load_config_file(f.name)
            self.assertEqual(cfg["a"]["b"], 1)

    def test_config_loads_ini(self):
        s = """
        [a]
        b = 1
        """
        ### Create a random tempoary file and write the string to it
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini") as f:
            f.write(s)
            f.flush()

            cfg = _load_config_file(f.name)
            self.assertEqual(cfg["a"]["b"], "1")


if __name__ == "__main__":
    unittest.main()
