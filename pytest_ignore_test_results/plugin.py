# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import typing as t
from fnmatch import fnmatch

from _pytest.config import Config
from _pytest.reports import BaseReport
from _pytest.stash import StashKey
from _pytest.terminal import TerminalReporter

from .utils import ExitCode, parse_ignore_results_files


class IgnoreTestResultsPlugin:
    def __init__(
        self,
        ignore_cases: t.Optional[t.List[str]],
        ignore_files: t.Optional[t.List[str]],
        strict_exit_code: bool = False,
    ):
        self.ignore_result_patterns = set(ignore_cases or [])
        self.ignore_result_patterns.update(parse_ignore_results_files(ignore_files or []))
        self.strict_exit_code = strict_exit_code

        # record the test cases, since in each test case, there may be sub test cases as well
        self._failed_test_cases: t.Dict[str, bool] = {}  # nodeid, is_result_ignored

    @property
    def failed_cases(self) -> t.List[str]:
        """
        Returns:
            List of failed test cases that are not ignored
        """
        return [case for case, is_result_ignored in self._failed_test_cases.items() if not is_result_ignored]

    @property
    def ignored_result_cases(self) -> t.List[str]:
        """
        Returns:
            List of failed test cases that are ignored
        """
        return [case for case, is_result_ignored in self._failed_test_cases.items() if is_result_ignored]

    def is_ignored_result_case(self, case_id: str) -> bool:
        for pattern in self.ignore_result_patterns:
            if case_id == pattern:
                return True
            if fnmatch(case_id, pattern):
                return True
        return False

    def pytest_report_teststatus(self, report: BaseReport) -> t.Optional[t.Tuple[str, str, str]]:
        if report.failed and report.nodeid not in self._failed_test_cases:
            self._failed_test_cases[report.nodeid] = self.is_ignored_result_case(report.nodeid)

        if report.when == 'call' and report.failed and self._failed_test_cases[report.nodeid]:
            return 'ignored', 'I', 'IGNORED'
        return None

    def pytest_terminal_summary(self, terminalreporter: TerminalReporter) -> None:
        if self.ignored_result_cases:
            terminalreporter.section('Ignored Result Cases', bold=True, yellow=True)
            terminalreporter.line('\n'.join(self.ignored_result_cases))

    def pytest_sessionfinish(self, session):
        if self.failed_cases:
            session.exitstatus = ExitCode.TESTS_FAILED
        elif self.ignored_result_cases:  # only ignored test cases are failed
            if self.strict_exit_code:
                session.exitstatus = ExitCode.ONLY_IGNORE_RESULT_CASES_FAILED
            else:
                session.exitstatus = ExitCode.OK


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


ignore_result_key = StashKey[IgnoreTestResultsPlugin]()


def pytest_configure(config: Config) -> None:
    config.stash[ignore_result_key] = IgnoreTestResultsPlugin(
        config.getoption('ignore_result_cases'),
        config.getoption('ignore_result_files'),
        config.getoption('strict_exit_code'),
    )

    config.pluginmanager.register(config.stash[ignore_result_key])


def pytest_unconfigure(config: Config) -> None:
    plugin = config.stash.get(ignore_result_key, None)
    if plugin:
        del config.stash[ignore_result_key]
        config.pluginmanager.unregister(plugin)
