# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import shutil
import typing as t
from pathlib import Path

import pytest

pytest_plugins = ['pytester']


@pytest.fixture(autouse=True)
def copy_test_script(pytester):
    shutil.copy(Path(__file__).parent / 'fixtures' / 'script.py', pytester.path / 'test_script.py')
    yield


def assert_outcomes(
    outcomes: t.Dict[str, int],
    passed: int = 0,
    skipped: int = 0,
    failed: int = 0,
    errors: int = 0,
    ignored: int = 0,
    xpassed: int = 0,
    xfailed: int = 0,
    warnings: t.Optional[int] = None,
    deselected: t.Optional[int] = None,
) -> None:
    """Assert that the specified outcomes appear with the respective
    numbers (0 means it didn't occur) in the text output from a test run."""
    __tracebackhide__ = True

    obtained = {
        'passed': outcomes.get('passed', 0),
        'skipped': outcomes.get('skipped', 0),
        'failed': outcomes.get('failed', 0),
        'errors': outcomes.get('errors', 0),
        'ignored': outcomes.get('ignored', 0),
        'xpassed': outcomes.get('xpassed', 0),
        'xfailed': outcomes.get('xfailed', 0),
    }
    expected = {
        'passed': passed,
        'skipped': skipped,
        'failed': failed,
        'errors': errors,
        'ignored': ignored,
        'xpassed': xpassed,
        'xfailed': xfailed,
    }
    if warnings is not None:
        obtained['warnings'] = outcomes.get('warnings', 0)
        expected['warnings'] = warnings
    if deselected is not None:
        obtained['deselected'] = outcomes.get('deselected', 0)
        expected['deselected'] = deselected
    assert obtained == expected
