class TestSystemInfos:
    def test_str(self, tag):
        assert str(tag) == tag.name
