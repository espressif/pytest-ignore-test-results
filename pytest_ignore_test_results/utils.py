# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import enum
import os
import typing as t


def parse_ignore_results_file(
    f: str,
) -> t.Set[str]:
    """
    Parse a file containing test cases or patterns to ignore

    Args:
        f: File to parse

    Returns:
        Set of test cases patterns to ignore
    """
    patterns = set()

    with open(f) as fr:
        for line in fr.readlines():
            if not line:
                continue
            if not line.strip():
                continue
            without_comments = line.split('#')[0].strip()
            if without_comments:
                patterns.add(without_comments)

    return patterns


def parse_ignore_results_files(
    files: t.List[str],
) -> t.Set[str]:
    """
    Parse a list of files containing test cases or patterns to ignore

    Args:
        files: List of files to parse

    Returns:
        Set of test cases patterns to ignore
    """
    patterns = set()

    for f in files:
        if not os.path.isfile(f):
            continue
        patterns.update(parse_ignore_results_file(f))

    return patterns


class ExitCode(enum.IntEnum):
    """
    Encodes the valid exit codes by pytest.

    0 - 5 is supported by native pytest.
    """

    #: Tests passed.
    OK = 0
    #: Tests failed.
    TESTS_FAILED = 1
    #: pytest was interrupted.
    INTERRUPTED = 2
    #: An internal error got in the way.
    INTERNAL_ERROR = 3
    #: pytest was misused.
    USAGE_ERROR = 4
    #: pytest couldn't find tests.
    NO_TESTS_COLLECTED = 5
    #: Only ignore result cases failed, and the `--strict-exit-code` flag is set.
    ONLY_IGNORE_RESULT_CASES_FAILED = 6
