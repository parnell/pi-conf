import os
import sys
import tempfile
import unittest

from platformdirs import site_config_dir

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

    def test_config_from_dict(self):
        from pi_conf import Config

        cfg = Config.from_dict({"a": 1})
        from pi_conf import AttrDict

        self.assertEqual(cfg.a, 1)

    def test_config_from_raw_dict(self):
        from pi_conf import Config

        cfg = Config({"a": 1})

        self.assertEqual(cfg.a, 1)

    def test_config_from_list_dict_nested(self):
        from pi_conf import Config

        cfg = Config.from_dict({"a": 1, "b": [{"c": 2}, {"d": 3}]})

        self.assertEqual(cfg.a, 1)
        self.assertEqual(cfg.b[0].c, 2)

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

    def test_config_dict_init(self):
        from pi_conf import Config

        cfg = Config({"a": 1})
        self.assertEqual(cfg.a, 1)
        self.assertEqual(cfg["a"], 1)
        self.assertEqual(cfg.get("a"), 1)

    def test_to_env_list(self):
        from pi_conf import Config

        cfg = Config({"a": [{"b": 1}, {"b": 2}]})
        envs = cfg.to_env(overwrite=True)
        self.assertEqual(envs, [("A0_B", "1"), ("A1_B", "2")])

    def test_to_env_list_dict(self):
        from pi_conf import Config

        cfg = Config({"a": [{"b": 1}, {"b": {"c": 2}}]})
        envs = cfg.to_env(overwrite=True)
        self.assertEqual(envs, [("A0_B", "1"), ("A1_B_C", "2")])

    def test_to_env_dict(self):
        from pi_conf import Config

        cfg = Config({"a": {"b": 1, "c": {"d": 2}}})
        envs = cfg.to_env(overwrite=True)
        self.assertEqual(envs, [("A_B", "1"), ("A_C_D", "2")])

    def test_to_env_str(self):
        from pi_conf import Config

        cfg = Config({"a": 1, "b": "2"})
        envs = cfg.to_env(overwrite=True)
        self.assertEqual(envs, [("A", "1"), ("B", "2")])

    def test_set_config_not_exists(self):
        from pi_conf import load_config, set_config

        with tempfile.TemporaryDirectory() as d:
            bn = os.path.basename(d)
            set_config(bn, config_directories=[d])
            with open(os.path.join(d, "config.toml"), "w") as f:
                f.write("a = 1")
                f.flush()

            cfg = load_config(bn, config_directories=[d])
            self.assertEqual(cfg.a, 1)

    def test_update_attrdict_with_attrdict(self):
        from pi_conf import AttrDict

        d1 = AttrDict({"a": 1, "b": 2})
        d2 = AttrDict({"a": 2, "c": 3})

        d1.update(d2)
        self.assertEqual(d1.a, 2)
        self.assertEqual(d1.b, 2)
        self.assertEqual(d1.c, 3)

    def test_update_attrdict_with_dict(self):
        from pi_conf import AttrDict

        d1 = AttrDict({"a": 1, "b": 2})
        d2 = {"b": {"a": 2, "c": 3}}

        d1.update(d2)
        self.assertEqual(d1.a, 1)
        self.assertEqual(d1.b.a, 2)
        self.assertEqual(d1.b.c, 3)



if __name__ == "__main__":
    test_file = "test_set_config_not_exists"
    if test_file:
        suite = unittest.TestSuite()
        suite.addTest(TestConfig(test_file))
        unittest.TextTestRunner().run(suite)
    else:
        unittest.main()
