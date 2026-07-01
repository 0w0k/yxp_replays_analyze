"""Unit tests for build_tianyan_wiki.py — clean() and parse_article()."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_tianyan_wiki as btw


class TestClean:
    def test_strips_tags(self):
        assert btw.clean("<b>bold</b>") == "bold"

    def test_nested_tags(self):
        assert btw.clean("<p><em>italic</em> text</p>") == "italic text"

    def test_plain_text(self):
        assert btw.clean("hello") == "hello"

    def test_strips_whitespace(self):
        assert btw.clean("  <span> hello </span>  ") == "hello"

    def test_empty(self):
        assert btw.clean("") == ""

    def test_only_tags(self):
        assert btw.clean("<br/><hr>") == ""


class TestParseArticle:
    def test_basic_article(self):
        body = '''
        <img src="https://example.com/assets/fates/Icon_FateStrategy_42.png">
        <h3>天衍名</h3><span class="muted">ID 42</span>
        <div class="phase-strip">
            <span class="phase-chip">攻击</span>
            <span class="phase-chip">权重 10 / 20 / 30</span>
        </div>
        <p>这是效果描述</p>
        '''
        result = btw.parse_article(body)
        assert result["name"] == "天衍名"
        assert result["icon"] == "Icon_FateStrategy_42.png"
        assert result["category"] == "攻击"
        assert result["weights"] == [10, 20, 30]
        assert result["desc"] == "这是效果描述"

    def test_multiple_tags(self):
        body = '''
        <img src="/Icon_FateStrategy_1.png">
        <h3>Fate</h3>
        <div class="phase-strip">
            <span class="phase-chip">防御</span>
            <span class="phase-chip">标签A</span>
            <span class="phase-chip">权重 5 / 15</span>
        </div>
        <p>desc</p>
        '''
        result = btw.parse_article(body)
        assert result["category"] == "防御"
        assert result["tags"] == ["标签A"]
        assert result["weights"] == [5, 15]

    def test_no_weights(self):
        body = '''
        <img src="/Icon_FateStrategy_2.png">
        <h3>NoWeight</h3>
        <div class="phase-strip">
            <span class="phase-chip">辅助</span>
        </div>
        <p>some desc</p>
        '''
        result = btw.parse_article(body)
        assert result["weights"] is None
        assert result["category"] == "辅助"

    def test_no_image(self):
        body = '<h3>NoImg</h3><p>desc</p>'
        result = btw.parse_article(body)
        assert result["icon"] is None
        assert result["name"] == "NoImg"

    def test_no_h3(self):
        body = '<img src="/x.png"><p>desc</p>'
        result = btw.parse_article(body)
        assert result["name"] == ""

    def test_no_description(self):
        body = '<img src="/x.png"><h3>Title</h3>'
        result = btw.parse_article(body)
        assert result["desc"] == ""

    def test_multiple_paragraphs_uses_last(self):
        body = '''
        <img src="/x.png">
        <h3>Title</h3>
        <p>first paragraph</p>
        <p>second paragraph</p>
        '''
        result = btw.parse_article(body)
        assert result["desc"] == "second paragraph"


class TestRegexPatterns:
    def test_h2_re(self):
        html = '<h2>通用<span class="muted">(70)</span></h2>'
        m = btw.H2_RE.search(html)
        assert m is not None
        assert btw.clean(m.group(1)) == "通用"
        assert int(m.group(2)) == 70

    def test_art_re(self):
        html = '<article class="fate-card" id="fate-strategy-12"><h3>X</h3></article>'
        m = btw.ART_RE.search(html)
        assert m is not None
        assert int(m.group(1)) == 12

    def test_weight_re(self):
        assert btw.WEIGHT_RE.match("权重 10 / 20 / 30")
        assert btw.WEIGHT_RE.match("  权重 5/15  ")
        assert not btw.WEIGHT_RE.match("攻击")
