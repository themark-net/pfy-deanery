"""The fixture stays red until add returns the sum of its arguments."""

import unittest

from add import add


class TestAdd(unittest.TestCase):
    def test_add_two_and_three(self):
        self.assertEqual(add(2, 3), 5)


if __name__ == "__main__":
    unittest.main()
