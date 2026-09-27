from services.urls import MAX_URLS, validate_urls


def test_validate_urls_normalizes_duplicates_and_keeps_query():
    result = validate_urls(
        [
            " https://Example.com/story#top ",
            "https://example.com/story",
            "https://example.com/other?lang=zh",
        ]
    )

    assert result.urls == (
        "https://example.com/story",
        "https://example.com/other?lang=zh",
    )
    assert result.duplicates == ("https://example.com/story",)
    assert result.errors == ()


def test_validate_urls_rejects_unsafe_schemes_and_local_hosts():
    result = validate_urls(
        ["file:///tmp/secret.txt", "http://localhost:8000/test", "http://127.0.0.1/a"]
    )

    assert result.urls == ()
    assert len(result.errors) == 3
    assert all("公开网页" in error or "地址" in error for error in result.errors)


def test_validate_urls_enforces_maximum_count():
    lines = [f"https://example.com/page-{index}" for index in range(MAX_URLS + 1)]

    result = validate_urls(lines)

    assert len(result.urls) == MAX_URLS
    assert any("最多" in error for error in result.errors)
    assert result.limit_exceeded is True
