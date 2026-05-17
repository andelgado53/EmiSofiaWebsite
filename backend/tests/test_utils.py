"""Unit tests for backend/app/utils.py."""

from __future__ import annotations

import pytest

from app.utils import generate_excerpt, normalise_labels, sanitise_html


# ---------------------------------------------------------------------------
# generate_excerpt
# ---------------------------------------------------------------------------


class TestGenerateExcerpt:
    def test_plain_text_under_limit_returned_unchanged(self):
        html = "<p>Hello world</p>"
        result = generate_excerpt(html)
        assert result == "Hello world"

    def test_truncates_to_200_characters(self):
        # 201 'a' characters inside a paragraph
        long_text = "a" * 201
        html = f"<p>{long_text}</p>"
        result = generate_excerpt(html)
        assert len(result) == 200
        assert result == "a" * 200

    def test_exactly_200_characters_not_truncated(self):
        text = "b" * 200
        html = f"<p>{text}</p>"
        result = generate_excerpt(html)
        assert result == text

    def test_strips_nested_tags(self):
        html = "<p>Hello <strong>bold</strong> and <em>italic</em></p>"
        result = generate_excerpt(html)
        assert result == "Hello bold and italic"

    def test_empty_html_returns_empty_string(self):
        assert generate_excerpt("") == ""

    def test_html_with_no_text_returns_empty_string(self):
        assert generate_excerpt("<p></p><ul></ul>") == ""

    def test_multiple_paragraphs_concatenated(self):
        html = "<p>First.</p><p>Second.</p>"
        result = generate_excerpt(html)
        assert result == "First.Second."

    def test_heading_text_included(self):
        html = "<h1>Title</h1><p>Body text.</p>"
        result = generate_excerpt(html)
        assert result == "TitleBody text."

    def test_result_is_never_longer_than_200(self):
        # Stress: very long multi-tag HTML
        html = "<p>" + "word " * 100 + "</p>"
        result = generate_excerpt(html)
        assert len(result) <= 200


# ---------------------------------------------------------------------------
# sanitise_html
# ---------------------------------------------------------------------------


class TestSanitiseHtml:
    def test_allowed_tags_preserved(self):
        html = "<p>Hello <strong>world</strong></p>"
        result = sanitise_html(html)
        assert "<p>" in result
        assert "<strong>" in result

    def test_disallowed_tag_stripped(self):
        html = "<p>Hello</p><script>alert('xss')</script>"
        result = sanitise_html(html)
        assert "<script>" not in result
        assert "Hello" in result

    def test_img_allowed_attributes_preserved(self):
        html = '<img src="https://cdn.example.com/photo.jpg" class="note-photo" alt="A photo">'
        result = sanitise_html(html)
        assert 'src="https://cdn.example.com/photo.jpg"' in result
        assert 'class="note-photo"' in result
        assert 'alt="A photo"' in result

    def test_img_disallowed_attribute_stripped(self):
        html = '<img src="https://cdn.example.com/photo.jpg" onclick="evil()">'
        result = sanitise_html(html)
        assert "onclick" not in result

    def test_heading_tags_preserved(self):
        for tag in ("h1", "h2", "h3"):
            html = f"<{tag}>Heading</{tag}>"
            result = sanitise_html(html)
            assert f"<{tag}>" in result

    def test_list_tags_preserved(self):
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = sanitise_html(html)
        assert "<ul>" in result
        assert "<li>" in result

    def test_ordered_list_preserved(self):
        html = "<ol><li>First</li></ol>"
        result = sanitise_html(html)
        assert "<ol>" in result

    def test_em_preserved(self):
        html = "<p><em>italic</em></p>"
        result = sanitise_html(html)
        assert "<em>" in result

    def test_disallowed_tag_content_kept(self):
        # The text inside a disallowed tag should still be present
        html = "<p>Hello <span>world</span></p>"
        result = sanitise_html(html)
        assert "world" in result
        assert "<span>" not in result

    def test_empty_string_returns_empty(self):
        assert sanitise_html("") == ""


# ---------------------------------------------------------------------------
# normalise_labels
# ---------------------------------------------------------------------------


class TestNormaliseLabels:
    def test_lowercases_labels(self):
        assert normalise_labels(["Life", "LESSONS"]) == ["life", "lessons"]

    def test_strips_whitespace(self):
        assert normalise_labels(["  life  ", "\tlessons\n"]) == ["life", "lessons"]

    def test_deduplicates_same_case(self):
        assert normalise_labels(["life", "life"]) == ["life"]

    def test_deduplicates_different_cases(self):
        result = normalise_labels(["Life", "life", "LIFE"])
        assert result == ["life"]

    def test_preserves_first_occurrence_order(self):
        result = normalise_labels(["Zebra", "Apple", "zebra", "Mango"])
        assert result == ["zebra", "apple", "mango"]

    def test_empty_list_returns_empty(self):
        assert normalise_labels([]) == []

    def test_empty_string_labels_excluded(self):
        result = normalise_labels(["", "  ", "life"])
        assert result == ["life"]

    def test_whitespace_only_label_excluded(self):
        assert normalise_labels(["   "]) == []

    def test_single_label_returned_normalised(self):
        assert normalise_labels(["  Hello World  "]) == ["hello world"]

    def test_mixed_duplicates_and_unique(self):
        result = normalise_labels(["A", "b", "A", "c", "B"])
        assert result == ["a", "b", "c"]
