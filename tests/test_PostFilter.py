import unittest

from code.classes import Package, Player, PostFilter


class TestPostFilter(unittest.TestCase):
    def test_return_contains1(self):
        pfilter = PostFilter(
            return_contains=("foo", "bar"),
            return_contains_exclusive=True,
        )

        assets = [
            Player(
                _id=1,
                dynasty_value=500,
                name="foo",
            ),
            Player(
                _id=2,
                dynasty_value=500,
                name="bar",
            ),
        ]

        package = Package(assets=assets)
        passes_filter = pfilter(package)

        # This should pass the filter
        assert passes_filter  # noqa: S101

    def test_return_contains2(self):
        pfilter = PostFilter(
            return_contains=("foo", "bar"),
            return_contains_exclusive=True,
        )

        assets = [
            Player(
                _id=1,
                dynasty_value=500,
                name="foo",
            ),
            Player(
                _id=2,
                dynasty_value=500,
                name="some other guy",
            ),
        ]

        package = Package(assets=assets)
        passes_filter = pfilter(package)

        # This should not pass the filter
        # - we're missing bar in the package
        assert not passes_filter  # noqa: S101

    def test_return_contains3(self):
        pfilter = PostFilter(
            return_contains=("foo", "bar"),
            return_contains_exclusive=True,
        )

        assets = [
            Player(
                _id=1,
                dynasty_value=500,
                name="foo",
            ),
        ]

        package = Package(assets=assets)
        passes_filter = pfilter(package)

        # This should not pass the filter
        # - we're missing bar in the package
        assert not passes_filter  # noqa: S101


if __name__ == "__main__":
    unittest.main()
