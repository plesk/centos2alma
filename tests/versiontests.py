# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
import unittest

from common import version


class KernelVersionTests(unittest.TestCase):

    def _check_parse(self, version_string, expected):
        kernel = version.KernelVersion(version_string)
        self.assertEqual(str(kernel), expected)

    def test_kernel_parse_simple(self):
        self._check_parse("3.10.0-1160.95.1.el7.x86_64", "3.10.0-1160.95.1.el7.x86_64")

    def test_kernel_parse_small_build(self):
        self._check_parse("3.10.0-1160.el7.x86_64", "3.10.0-1160.el7.x86_64")

    def test_kernel_parse_large_build(self):
        self._check_parse("2.25.16-1.2.3.4.5.el7.x86_64", "2.25.16-1.2.3.4.5.el7.x86_64")

    def test_kernel_parse_no_build(self):
        self._check_parse("3.10.0.el7.x86_64", "3.10.0.el7.x86_64")

    def test_compare_simple_equal(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        self.assertEqual(kernel1, kernel2)

    def test_compare_simple_less_build(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.10.0-1160.95.2.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_simple_less_patch(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.10.2-1160.95.1.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_simple_less_minor(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.11.0-1160.95.1.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_simple_less_major(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("4.10.0-1160.95.1.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_simple_build_vs_short(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.10.0-1160.el7.x86_64")
        self.assertGreater(kernel1, kernel2)

    def test_find_last_kernel(self):
        kernels_strings = [
            "3.10.0-1160.76.1.el7.x86_64",
            "3.10.0-1160.95.1.el7.x86_64",
            "3.10.0-1160.el7.x86_64",
            "3.10.0-1160.45.1.el7.x86_64",
        ]
        kernels = [version.KernelVersion(s) for s in kernels_strings]

        self.assertEqual(str(max(kernels)), "3.10.0-1160.95.1.el7.x86_64")

    def test_sort_kernels(self):
        kernels_strings = [
            "3.10.0-1160.76.1.el7.x86_64",
            "3.10.0-1160.95.1.el7.x86_64",
            "3.10.0-1160.el7.x86_64",
            "3.10.0-1160.45.1.el7.x86_64",
        ]
        kernels = [version.KernelVersion(s) for s in kernels_strings]
        kernels.sort(reverse=True)

        expected = [
            "3.10.0-1160.95.1.el7.x86_64",
            "3.10.0-1160.76.1.el7.x86_64",
            "3.10.0-1160.45.1.el7.x86_64",
            "3.10.0-1160.el7.x86_64",
        ]

        self.assertEqual([str(k) for k in kernels], expected)
