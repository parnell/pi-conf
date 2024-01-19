import os
import sys
import unittest
from dataclasses import dataclass, field

from pi_conf import AttrDict, Config

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
        @dataclass
        class MyConfig(Config):
            a: int = 1

        cfg = MyConfig()
        self.assertEqual(cfg.a, 1)

    def test_dataclass_subclass_from_dict(self):
        @dataclass
        class MyConfig(Config):
            a: int = 1

        cfg = MyConfig.from_dict({"a": 1})
        self.assertEqual(cfg.a, 1)
        self.assertEqual(type(cfg), MyConfig)

    def test_config_dict_init(self):
        @dataclass
        class MyConfig(Config):
            a: int = 1
            b: int = 2

        cfg = MyConfig(**{"a": 1, "b": 2})
        self.assertEqual(cfg.a, 1)
        self.assertEqual(cfg["a"], 1)

        self.assertEqual(cfg.get("a"), 1)
        self.assertEqual(cfg.b, 2)
        self.assertEqual(cfg["b"], 2)
        self.assertEqual(cfg.get("b"), 2)

    # def test_dataclass_subclass_from_dict_recursive(self):
    #     ## TODO fix nested same class
    #     @dataclass
    #     class MyConfig(Config):
    #         a: int = 1
    #         b: dict = field(default_factory=dict)

    #     cfg = MyConfig.from_dict({"a": 1, "b":{"a": 2}}, _nested_same_class=True)
    #     self.assertEqual(cfg.a, 1)
    #     self.assertEqual(cfg["a"], 1)
    #     self.assertEqual(cfg.b.a, 2)
    #     self.assertEqual(cfg["b"]["a"], 2)
    #     self.assertEqual(type(cfg), MyConfig)
    #     self.assertEqual(type(cfg.a), MyConfig)

    def test_dataclass_subclass_from_dict_recursive_nested_false(self):
        @dataclass
        class MyConfig(Config):
            a: int = 1
            b: AttrDict = field(default_factory=AttrDict)

        cfg = MyConfig.from_dict({"a": 1, "b": {"c": 2}}, _nested_same_class=False)
        self.assertEqual(cfg.a, 1)
        self.assertEqual(cfg["a"], 1)
        self.assertEqual(cfg.b.c, 2)
        self.assertEqual(cfg["b"]["c"], 2)
        self.assertEqual(type(cfg), MyConfig)
        self.assertEqual(type(cfg.a), int)
        self.assertEqual(type(cfg.b), AttrDict)


if __name__ == "__main__":
    test_file = ""
    if test_file:
        suite = unittest.TestSuite()
        suite.addTest(TestSubclass(test_file))
        runner = unittest.TextTestRunner()
        runner.run(suite)
    else:
        unittest.main()
