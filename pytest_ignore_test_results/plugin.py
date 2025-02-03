# SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from _pytest.config import (
    Config,
)
from _pytest.stash import (
    StashKey,
)

from .ignore_results import (
    IgnoreTestResultsPlugin,
)


def pytest_addoption(parser):
    group = parser.getgroup('pytest_ignore_test_results')
    group.addoption(
        '--ignore-result-cases',
        nargs='+',
        help='Space separated list of test cases or patterns to ignore',
    )
    group.addoption(
        '--ignore-result-files',
        nargs='+',
        help='Space separated list of files to ignore, each line of the file is a test case or a pattern',
    )
    group.addoption(
        '--strict-exit-code',
        action='store_true',
        help='Set the Exit code to 6 if only ignored test cases are failed. If not set, the exit code will be 0',
    )
    group.addoption(
        '--ignore-no-tests-collected-error',
        action='store_true',
        help='Ignore the error if no tests are collected',
    )


ignore_result_key = StashKey[IgnoreTestResultsPlugin]()


def pytest_addhooks(pluginmanager):
    from . import (
        hooks,
    )

    pluginmanager.add_hookspecs(hooks)


def pytest_configure(config: Config) -> None:
    config.stash[ignore_result_key] = IgnoreTestResultsPlugin(
        config,
        ignore_cases=config.getoption('ignore_result_cases'),
        ignore_files=config.getoption('ignore_result_files'),
        strict_exit_code=config.getoption('strict_exit_code'),
        ignore_no_tests_collected_error=config.getoption('ignore_no_tests_collected_error'),
    )

    config.pluginmanager.register(config.stash[ignore_result_key])


def pytest_unconfigure(config: Config) -> None:
    plugin = config.stash.get(ignore_result_key, None)
    if plugin:
        del config.stash[ignore_result_key]
        config.pluginmanager.unregister(plugin)
