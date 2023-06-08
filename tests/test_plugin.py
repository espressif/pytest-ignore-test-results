# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import re

from conftest import assert_outcomes

from pytest_ignore_test_results.utils import ExitCode


def test_basic_script(pytester):
    result = pytester.runpytest('-vv')
    assert result.ret == 1

    assert_outcomes(result.parseoutcomes(), failed=2, passed=1, skipped=2, xfailed=3, ignored=0)


def test_ignore_all_failed_cases(pytester):
    result = pytester.runpytest(
        '-vv',
        '--ignore-result-cases',
        '*test_failed_*',
    )
    assert result.ret == 0
    assert_outcomes(result.parseoutcomes(), failed=0, passed=1, skipped=2, xfailed=3, ignored=2)


def test_ignore_part_of_failed_cases(pytester):
    result = pytester.runpytest(
        '-vv',
        '--ignore-result-cases',
        '*test_failed_1',
    )
    assert result.ret == 1
    assert_outcomes(result.parseoutcomes(), failed=1, passed=1, skipped=2, xfailed=3, ignored=1)


def test_ignored_junit_report_same(pytester):
    pytester.runpytest(
        '-vv',
        '--ignore-result-cases',
        '*test_failed_1',
        '--junitxml=report_1.xml',
    )
    pytester.runpytest(
        '-vv',
        '--junitxml=report_2.xml',
    )

    def replace_time(s: str):
        s = re.compile('time=".+"').sub('time="0.000"', s)
        s = re.compile('timestamp=".+"').sub('timestamp="0.000"', s)
        return s

    with open(pytester.path / 'report_1.xml') as f1:
        with open(pytester.path / 'report_2.xml') as f2:
            assert replace_time(f1.read()) == replace_time(f2.read())


def test_ignored_exitcode(pytester):
    result = pytester.runpytest(
        '-vv',
        '--ignore-result-cases',
        '*test_failed*',
    )
    assert result.ret == ExitCode.OK

    result = pytester.runpytest(
        '-vv',
        '--ignore-result-cases',
        '*test_failed*',
        '--strict-exit-code',
    )
    assert result.ret == ExitCode.ONLY_IGNORE_RESULT_CASES_FAILED
