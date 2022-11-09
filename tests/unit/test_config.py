#!/usr/bin/env python3
"""Test functionality in the config module."""
import os
import stat

import configargparse

import snafu.config


def test_check_file_returns_bool_as_expected(tmpdir):
    """Test that the check_file function will return ``True`` and ``False`` when it is supposed to."""

    tmpdir.chmod(stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    test_file = tmpdir.join("testfile.txt")
    test_file.write("some content")
    test_file_path = test_file.realpath()
    assert test_file.check()

    test_perms = (
        (os.R_OK, stat.S_IREAD),
        (os.R_OK | os.W_OK, stat.S_IREAD | stat.S_IWRITE),
        (os.R_OK | os.W_OK | os.EX_OK, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC),
    )

    with tmpdir.as_cwd():
        for check, perm in test_perms:
            test_file.chmod(0)
            assert snafu.config.check_file(test_file_path, perms=check) is False
            test_file.chmod(perm)
            assert snafu.config.check_file(test_file_path, perms=check) is True


def test_none_or_type_function():
    """Test that the none_or_type function returns function that casts values only when they aren't None."""

    tests = (
        (int, 1),
        (int, "1"),
        (str, "hey"),
        (str, 2),
        (dict, (("a", 1), ("b", 2))),
    )

    for expected_type, value in tests:
        wrapped = snafu.config.none_or_type(expected_type)
        assert wrapped(None) is None
        assert wrapped(value) == expected_type(value)
        assert isinstance(wrapped(value), expected_type)


class TestConfig:
    """Test functionality of Config class."""

    test_args = (
        snafu.config.ConfigArgument("param1", type=int),
        snafu.config.ConfigArgument("param2", type=str),
        snafu.config.ConfigArgument("--param3", type=str, env_var="param3"),
        snafu.config.ConfigArgument("--param4", type=int, env_var="p4"),
    )
    test_input = ["1234", "my_string", "--param3", "1234", "--param4", "4321"]

    @staticmethod
    def verify_args(config: snafu.config.Config):
        """Verify that config contains expected args from cls.test_args and cls.test_input."""

        assert config.param1 == 1234
        assert config.param2 == "my_string"
        assert config.param3 == "1234"
        assert config.param4 == 4321

    @staticmethod
    def get_config_instance() -> snafu.config.Config:
        """Return a new Config instance with tool_name set to 'TEST'."""
        try:
            configargparse.init_argument_parser()
        except ValueError:
            del configargparse._parsers["default"]  # pylint: disable=W0212
            configargparse.init_argument_parser()
        return snafu.config.Config("TEST")

    def test_init_creates_argparser(self):
        """
        Test that init creates an instance of ``configargparse.ArgParser``.

        If this changes, then this test suite and benchmark options will need to be updated, as it's
        expected that arguments to ``add_argument`` will change.
        """

        config = self.get_config_instance()
        assert isinstance(config.parser, configargparse.ArgumentParser)

    def test_can_add_args_and_parse_using_add_argument_method(self):
        """Test that we can populate a parser and parse args using the ``add_argument`` method."""

        config = self.get_config_instance()
        for arg in self.test_args:
            config.add_argument(*arg.args, **arg.kwargs)
        config.parse_args(self.test_input)
        self.verify_args(config)

    def test_can_add_and_parse_using_populate_parser_method(self):
        """Test that we can populate a parser and parse args using the ``populate_parser`` method."""

        config = self.get_config_instance()
        config.populate_parser(self.test_args)
        config.parse_args(self.test_input)
        self.verify_args(config)

    def test_can_get_env_param_mapping(self):
        """Test that env_to_params attribute becomes populated appropriately as we add arguments."""

        config = self.get_config_instance()
        assert not config.env_to_params
        config.populate_parser(self.test_args)
        assert config.env_to_params == {"param3": "param3", "p4": "param4"}

    def test_get_env_returns_correct_env_mappings(self):
        """Tests that the env_to_params attribute will return the correct env variable mappings."""

        config = self.get_config_instance()
        config.populate_parser(self.test_args)
        assert config.get_env() == dict(os.environ)

        config.parse_args(self.test_input)
        self.verify_args(config)

        env = config.get_env()
        assert env["param3"] == str(config.param3)
        assert env["p4"] == str(config.param4)
        for key, val in os.environ.items():
            assert env[key] == val
