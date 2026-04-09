from gtb.models import BookResult
from gtb.search import parallel_search
from gtb.sources.base import Source


class FakeSourceA(Source):
    name = "fake_a"

    def search(self, query):
        return [
            BookResult(
                title="Book A", author="Auth A", md5="AAAA1111AAAA1111AAAA1111AAAA1111",
                extension="pdf", size_bytes=5_000_000, language="en", year="2020",
                source="fake_a", mirror_url="http://example.com/a",
            ),
            BookResult(
                title="Shared Book", author="Shared", md5="SHARED11SHARED11SHARED11SHARED11",
                extension="pdf", size_bytes=5_000_000, language="en", year="2020",
                source="fake_a", mirror_url="http://example.com/shared_a",
            ),
        ]

    def resolve_download_url(self, book):
        return "http://example.com/download_a"


class FakeSourceB(Source):
    name = "fake_b"

    def search(self, query):
        return [
            BookResult(
                title="Book B", author="Auth B", md5="BBBB2222BBBB2222BBBB2222BBBB2222",
                extension="epub", size_bytes=1_000_000, language="en", year="2021",
                source="fake_b",
            ),
            BookResult(
                title="Shared Book", author="Shared", md5="SHARED11SHARED11SHARED11SHARED11",
                extension="pdf", size_bytes=5_000_000, language="en", year="2020",
                source="fake_b", mirror_url="http://example.com/shared_b",
            ),
        ]

    def resolve_download_url(self, book):
        return "http://example.com/download_b"


class FakeSourceFail(Source):
    name = "fail"

    def search(self, query):
        raise ConnectionError("boom")

    def resolve_download_url(self, book):
        return None


def test_parallel_search_merges_results():
    sources = [FakeSourceA(), FakeSourceB()]
    results = parallel_search("test", sources)
    assert len(results) == 3
    md5s = {r.md5 for r in results}
    assert "AAAA1111AAAA1111AAAA1111AAAA1111" in md5s
    assert "BBBB2222BBBB2222BBBB2222BBBB2222" in md5s
    assert "SHARED11SHARED11SHARED11SHARED11" in md5s


def test_parallel_search_dedupes_by_md5():
    sources = [FakeSourceA(), FakeSourceB()]
    results = parallel_search("test", sources)
    md5_counts = {}
    for r in results:
        md5_counts[r.md5] = md5_counts.get(r.md5, 0) + 1
    assert md5_counts["SHARED11SHARED11SHARED11SHARED11"] == 1


def test_parallel_search_survives_source_failure():
    sources = [FakeSourceA(), FakeSourceFail()]
    results = parallel_search("test", sources)
    assert len(results) == 2
