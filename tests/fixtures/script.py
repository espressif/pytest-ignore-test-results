# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import pytest


# Failed
def test_failed_1():
    assert False


def test_failed_2():
    pytest.fail('failed')


# Skipped
def test_skipped_1():
    pytest.xfail('xfailed')
    assert False


def test_skipped_2():
    pytest.skip('skipped')
    assert False


@pytest.mark.xfail(reason='skipped')
def test_skipped_3():
    assert False


@pytest.mark.xfail(reason='skipped', run=False)
def test_skipped_4():
    assert False


@pytest.mark.skip(reason='skipped')
def test_skipped_5():
    assert False


# Passed
def test_passed_1():
    assert True
