# SPDX-FileCopyrightText: 2023-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import xml.etree.ElementTree as ET

import pytest
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


def _make_unity_cases_conftest(pytester, unity_cases, legacy_cases=()):
    embedded = pytester.path / 'pytest_embedded'
    embedded.mkdir()
    (embedded / '__init__.py').write_text('')
    (embedded / 'unity.py').write_text('import pytest\nUnityCasesStashKey = pytest.StashKey[list]()\n')
    pytester.makeconftest(f"""
import xml.etree.ElementTree as ET
from types import SimpleNamespace

from pytest_embedded.unity import UnityCasesStashKey
from pytest_ignore_test_results.ignore_results import ChildCase, ChildCasesStashKey

_UNITY_CASES = {unity_cases!r}
_LEGACY_CASES = {legacy_cases!r}

def pytest_runtest_makereport(item, call):
    if call.when == 'call':
        item.stash[UnityCasesStashKey] = [SimpleNamespace(name=name, result=result) for name, result in _UNITY_CASES]
        if _LEGACY_CASES:
            item.config.stash[ChildCasesStashKey] = {{
                item.nodeid: [ChildCase(name, result) for name, result in _LEGACY_CASES]
            }}

def pytest_sessionfinish(session):
    junit_path = session.config.option.xmlpath
    if not junit_path:
        return
    tree = ET.parse(junit_path)
    testsuite = tree.getroot().find('testsuite')
    for name, result in (*_UNITY_CASES, *_LEGACY_CASES):
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


def test_ignore_unity_child_cases(pytester):
    _make_unity_cases_conftest(pytester, [('unity_pass', 'passed'), ('unity_fail', 'failed')])

    result = pytester.runpytest_subprocess(
        '-k', 'test_failed_2', '--ignore-result-cases', 'unity_fail', '--junitxml=report.xml'
    )
    assert result.ret == ExitCode.OK
    assert_outcomes(result.parseoutcomes(), ignored=1, deselected=7)

    cases = _junit_cases(pytester)
    assert cases['unity_fail'].get('is_ignored') == '1'
    assert cases['test_failed_2'].get('is_ignored') == '1'
    assert 'is_ignored' not in cases['unity_pass'].attrib


def test_unity_child_cases_do_not_override_legacy_cases(pytester):
    _make_unity_cases_conftest(pytester, [('unity_fail', 'failed')], [('legacy_fail', 'failed')])

    result = pytester.runpytest_subprocess(
        '-k', 'test_failed_2', '--ignore-result-cases', 'legacy_fail', '--junitxml=report.xml'
    )
    assert result.ret == ExitCode.OK
    assert_outcomes(result.parseoutcomes(), ignored=1, deselected=7)

    cases = _junit_cases(pytester)
    assert cases['legacy_fail'].get('is_ignored') == '1'
    assert 'is_ignored' not in cases['unity_fail'].attrib


def test_unignored_unity_child_failure_keeps_test_failed(pytester):
    _make_unity_cases_conftest(pytester, [('unity_ignored', 'failed'), ('unity_failed', 'failed')])

    result = pytester.runpytest_subprocess(
        '-k', 'test_failed_2', '--ignore-result-cases', 'unity_ignored', '--junitxml=report.xml'
    )
    assert result.ret == ExitCode.TESTS_FAILED
    assert_outcomes(result.parseoutcomes(), failed=1, deselected=7)

    cases = _junit_cases(pytester)
    assert cases['unity_ignored'].get('is_ignored') == '1'
    assert 'is_ignored' not in cases['unity_failed'].attrib
    assert 'is_ignored' not in cases['test_failed_2'].attrib


def test_unity_cases_survive_xdist_report_transport(pytester):
    pytest.importorskip('xdist')
    _make_unity_cases_conftest(pytester, [('unity_fail', 'failed')])

    result = pytester.runpytest_subprocess('-n', '2', '-k', 'test_failed_2', '--ignore-result-cases', 'unity_fail')
    assert result.ret == ExitCode.OK
    assert_outcomes(result.parseoutcomes(), ignored=1)


def test_legacy_cases_take_precedence_after_xdist_report_transport(pytester):
    pytest.importorskip('xdist')
    _make_unity_cases_conftest(pytester, [('unity_fail', 'failed')], [('legacy_fail', 'failed')])

    result = pytester.runpytest_subprocess('-n', '2', '-k', 'test_failed_2', '--ignore-result-cases', 'legacy_fail')
    assert result.ret == ExitCode.OK
    assert_outcomes(result.parseoutcomes(), ignored=1)


def test_older_pytest_embedded_without_unity_key(pytester):
    embedded = pytester.path / 'pytest_embedded'
    embedded.mkdir()
    (embedded / '__init__.py').write_text('')
    (embedded / 'unity.py').write_text('')

    result = pytester.runpytest_subprocess(
        '-k', 'test_failed_2', '--ignore-result-cases', 'test_script.py::test_failed_2'
    )
    assert result.ret == ExitCode.OK
    assert_outcomes(result.parseoutcomes(), ignored=1, deselected=7)


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
