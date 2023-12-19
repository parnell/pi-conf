import os
import sys
import unittest

from pi_conf import Config

basedir = os.path.abspath(os.getcwd())
sys.path.append(basedir)


class TestSubclass(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def test_dataclass_subclass(self):
        class MyConfig(Config):
            a: int = 1

        cfg = MyConfig()
        self.assertEqual(cfg.a, 1)

    def test_dataclass_subclass_from_dict(self):
        class MyConfig(Config):
            a: int = 1

        cfg = MyConfig.from_dict({"a": 1})
        self.assertEqual(cfg.a, 1)
        self.assertEqual(type(cfg), MyConfig)

    def test_dataclass_subclass_from_dict_recursive(self):
        class MyConfig(Config):
            a: int = 1

        cfg = MyConfig.from_dict({"a": {"b": 1}})
        self.assertEqual(cfg.a.b, 1)
        self.assertEqual(type(cfg), MyConfig)
        self.assertEqual(type(cfg.a), MyConfig)



if __name__ == "__main__":
    unittest.main()
