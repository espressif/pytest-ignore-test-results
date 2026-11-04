# SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import xml.etree.ElementTree as ET

from conftest import (
    assert_outcomes,
)

from pytest_ignore_test_results.utils import (
    ExitCode,
)


def _make_child_cases_conftest(pytester, child_cases):
    pytester.makeconftest(f"""
import xml.etree.ElementTree as ET

import pytest
from pytest_ignore_test_results.ignore_results import ChildCase, ChildCasesStashKey

_CHILD_CASES = {child_cases!r}

def pytest_runtest_makereport(item, call):
    if call.when == 'call':
        item.config.stash[ChildCasesStashKey] = {{
            item.nodeid: [ChildCase(name, result) for name, result in _CHILD_CASES]
        }}

@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session):
    junit_path = session.config.option.xmlpath
    if not junit_path:
        return
    tree = ET.parse(junit_path)
    testsuite = tree.getroot().find('testsuite')
    for name, result in _CHILD_CASES:
        testcase = ET.SubElement(testsuite, 'testcase', {{'name': name}})
        if result == 'failed':
            ET.SubElement(testcase, 'failure')
    tree.write(junit_path)
""")


def _junit_cases(pytester):
    tree = ET.parse(pytester.path / 'report.xml')
    return {testcase.get('name'): testcase for testcase in tree.findall('.//testcase')}


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


def test_ignored_junit_report_marks_known_failures(pytester):
    result = pytester.runpytest(
        '-vv',
        '--ignore-result-cases',
        '*test_failed_1',
        '--junitxml=report.xml',
    )
    assert result.ret == 1

    cases = _junit_cases(pytester)
    assert cases['test_failed_1'].get('is_ignored') == '1'
    assert cases['test_failed_1'].find('failure') is not None
    assert 'is_ignored' not in cases['test_failed_2'].attrib
    assert 'is_ignored' not in cases['test_passed_1'].attrib


def test_ignored_junit_report_marks_errors(pytester):
    pytester.makepyfile(
        **{
            'test_error.py': """
        import pytest

        @pytest.fixture
        def broken_fixture():
            raise RuntimeError('setup failed')

        def test_error(broken_fixture):
            pass
    """
        }
    )
    result = pytester.runpytest(
        'test_error.py',
        '--ignore-result-cases',
        'test_error.py::test_error',
        '--junitxml=report.xml',
    )
    assert result.ret == ExitCode.OK

    cases = _junit_cases(pytester)
    assert cases['test_error'].get('is_ignored') == '1'
    assert cases['test_error'].find('error') is not None


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


def test_ignore_child_cases(pytester):
    _make_child_cases_conftest(pytester, [('child_case_1', 'passed'), ('child_case_2', 'failed')])

    result = pytester.runpytest(
        '-vv',
        '-k',
        'test_failed_2',
    )
    assert result.ret == 1
    assert_outcomes(result.parseoutcomes(), failed=1, passed=0, skipped=0, xfailed=0, ignored=0, deselected=7)

    result = pytester.runpytest(
        '-vv',
        '-k',
        'test_failed_2',
        '--ignore-result-cases',
        'child_case_2',
        '--junitxml=report.xml',
    )
    assert_outcomes(result.parseoutcomes(), failed=0, passed=0, skipped=0, xfailed=0, ignored=1, deselected=7)

    cases = _junit_cases(pytester)
    assert cases['test_failed_2'].get('is_ignored') == '1'
    assert cases['child_case_2'].get('is_ignored') == '1'
    assert 'is_ignored' not in cases['child_case_1'].attrib


def test_ignore_main_case_with_child_cases(pytester):
    _make_child_cases_conftest(pytester, [('child_case_1', 'passed'), ('child_case_2', 'failed')])

    result = pytester.runpytest(
        '-vv',
        '-k',
        'test_failed_2',
    )
    assert result.ret == 1
    assert_outcomes(result.parseoutcomes(), failed=1, passed=0, skipped=0, xfailed=0, ignored=0, deselected=7)

    result = pytester.runpytest(
        '-vv',
        '-k',
        'test_failed_2',
        '--ignore-result-cases',
        'test_script.py::test_failed_2',
        '--junitxml=report.xml',
    )
    assert_outcomes(result.parseoutcomes(), failed=0, passed=0, skipped=0, xfailed=0, ignored=1, deselected=7)

    cases = _junit_cases(pytester)
    assert cases['test_failed_2'].get('is_ignored') == '1'
    assert cases['child_case_2'].get('is_ignored') == '1'


def test_parent_case_not_marked_with_unignored_child_failure(pytester):
    _make_child_cases_conftest(pytester, [('child_case_1', 'failed'), ('child_case_2', 'failed')])

    result = pytester.runpytest(
        '-k',
        'test_failed_2',
        '--ignore-result-cases',
        'child_case_2',
        '--junitxml=report.xml',
    )
    assert result.ret == 1

    cases = _junit_cases(pytester)
    assert 'is_ignored' not in cases['test_failed_2'].attrib
    assert 'is_ignored' not in cases['child_case_1'].attrib
    assert cases['child_case_2'].get('is_ignored') == '1'


def test_ignore_no_collect_error(pytester):
    result = pytester.runpytest(
        '-k',
        'not_exists',
    )
    assert result.ret == ExitCode.NO_TESTS_COLLECTED

    result = pytester.runpytest(
        '-k',
        'not_exists',
        '--ignore-no-tests-collected-error',
    )
    assert result.ret == ExitCode.OK
