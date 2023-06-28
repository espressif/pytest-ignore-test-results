# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import typing as t
from fnmatch import fnmatch

import pytest
from _pytest.config import Config
from _pytest.python import Function
from _pytest.reports import BaseReport, TestReport
from _pytest.stash import StashKey
from _pytest.terminal import TerminalReporter

from .utils import ExitCode, parse_ignore_results_files

if t.TYPE_CHECKING:
    from typing import Literal


class ChildCase:
    """
    Represents a child case of a test case.
    """

    def __init__(self, name: str, result: "Literal['passed', 'failed', 'skipped']"):
        self.name = name
        self.result = result


# config stash
# {nodeid: list[ChildCase]}
ChildCasesStashKey = StashKey[t.Dict[str, t.List[ChildCase]]]()


class IgnoreTestResultsPlugin:
    def __init__(
        self,
        config: Config,
        *,
        ignore_cases: t.Optional[t.List[str]] = None,
        ignore_files: t.Optional[t.List[str]] = None,
        strict_exit_code: bool = False,
    ):
        self.config = config
        self.config.stash.setdefault(ChildCasesStashKey, {})

        self.ignore_result_patterns = set(ignore_cases or [])
        self.ignore_result_patterns.update(parse_ignore_results_files(ignore_files or []))
        self.strict_exit_code = strict_exit_code

        # record the test cases, since in each test case, there may be child cases as well
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

    def pytest_custom_test_case_name(self, item: Function) -> str:
        return item.nodeid

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_runtest_makereport(self, item: Function) -> BaseReport:
        outcome = yield
        rep = outcome.get_result()
        rep.custom_test_case_name = self.config.hook.pytest_custom_test_case_name(item=item)

    def pytest_report_teststatus(self, report: TestReport) -> t.Optional[t.Tuple[str, str, str]]:
        """
        Check if the test case is ignored or not. If there are child cases, check them instead. The result of the test
        case itself will be ignored.

        Note:
            Remember that this function will be called three times (setup, call, teardown) for each item.
            We only care about the call phase of the test case.
        """
        if not report.failed:
            return

        if report.when in ['setup', 'teardown']:
            # setup and teardown failures we only record them
            custom_test_case_name = getattr(report, 'custom_test_case_name', report.nodeid)
            self._failed_test_cases[custom_test_case_name] = self.is_ignored_result_case(custom_test_case_name)
            return

        child_cases = self.config.stash[ChildCasesStashKey].get(report.nodeid, [])
        if not child_cases:
            # no child cases, we use the test case itself
            custom_test_case_name = getattr(report, 'custom_test_case_name', report.nodeid)
            self._failed_test_cases[custom_test_case_name] = self.is_ignored_result_case(custom_test_case_name)
            if self._failed_test_cases[custom_test_case_name]:
                return 'ignored', 'I', 'IGNORED'
        else:
            # there are child cases, we use child cases instead
            has_failed = False
            has_ignored = False
            for child_case in child_cases:
                if child_case.result == 'failed':
                    has_failed = True
                    self._failed_test_cases[child_case.name] = self.is_ignored_result_case(child_case.name)
                    if self._failed_test_cases[child_case.name]:
                        has_ignored = True

            if has_failed:
                if has_ignored:
                    return 'ignored', 'I', 'IGNORED CHILD CASES'
                else:
                    return 'failed', 'F', 'FAILED CHILD CASES'

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
