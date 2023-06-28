# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import pytest


@pytest.hookspec(firstresult=True)
def pytest_custom_test_case_name(item) -> str:
    """
    Args:
        item: pytest item

    Returns:
        The name of the test case. By default, it is the nodeid of the test case.
    """
