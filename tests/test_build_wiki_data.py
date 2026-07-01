"""Unit tests for build_wiki_data.py — pure HTML parsing helpers."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_wiki_data as bwd


class TestFam:
    def test_strips_level(self):
        assert bwd.fam(10020001) == 10000001

    def test_level_zero(self):
        assert bwd.fam(10000001) == 10000001

    def test_zero(self):
        assert bwd.fam(0) == 0


class TestH1:
    def test_basic(self):
        assert bwd.h1("<html><h1>火球术</h1></html>") == "火球术"

    def test_with_whitespace(self):
        assert bwd.h1("<h1>  Ice Spike  </h1>") == "Ice Spike"

    def test_no_h1(self):
        assert bwd.h1("<html><h2>not h1</h2></html>") == ""

    def test_first_h1_only(self):
        assert bwd.h1("<h1>First</h1><h1>Second</h1>") == "First"


class TestEnName:
    def test_extracts_en_name(self):
        html = '<p class="original-name"><span>CN</span>Fireball</p>'
        assert bwd.en_name(html) == "Fireball"

    def test_strips_inner_tags(self):
        html = '<p class="original-name"><span>CN</span><em>Fire</em>ball</p>'
        assert bwd.en_name(html) == "Fireball"

    def test_no_match(self):
        assert bwd.en_name("<p>nothing</p>") == ""

    def test_whitespace_stripped(self):
        html = '<p class="original-name"><span>CN</span>  Spell  </p>'
        assert bwd.en_name(html) == "Spell"


class TestLinkSect:
    def test_sect_slug(self):
        html = '<a href="/zh/sects/cloud-spirit-sword-sect.html">link</a>'
        assert bwd.link_sect(html) == "sw"

    def test_heptastar(self):
        html = '<a href="/zh/sects/heptastar-pavilion.html">link</a>'
        assert bwd.link_sect(html) == "he"

    def test_five_elements(self):
        html = '<a href="/zh/sects/five-elements-alliance.html">link</a>'
        assert bwd.link_sect(html) == "fe"

    def test_duan_xuan(self):
        html = '<a href="/zh/sects/duan-xuan-sect.html">link</a>'
        assert bwd.link_sect(html) == "dx"

    def test_side_job_slug(self):
        html = '<a href="/zh/side-jobs/elixirist.html">link</a>'
        assert bwd.link_sect(html) == "el"

    def test_character_link(self):
        html = '<a href="/zh/characters/1000005.html">link</a>'
        assert bwd.link_sect(html) == "sw"  # leading digit 1 -> sw

    def test_character_link_he(self):
        html = '<a href="/zh/characters/2000001.html">link</a>'
        assert bwd.link_sect(html) == "he"  # leading digit 2 -> he

    def test_no_match(self):
        html = '<a href="/zh/items/something.html">link</a>'
        assert bwd.link_sect(html) is None


class TestBreadcrumbCat:
    def test_extracts_third_segment(self):
        html = '<nav class="breadcrumb">Home › Cards › 融汇 › Detail</nav>'
        assert bwd.breadcrumb_cat(html) == "融汇"

    def test_no_breadcrumb(self):
        assert bwd.breadcrumb_cat("<p>no nav</p>") == ""

    def test_short_breadcrumb(self):
        html = '<nav class="breadcrumb">Home › Cards</nav>'
        assert bwd.breadcrumb_cat(html) == ""

    def test_strips_tags(self):
        html = '<nav class="breadcrumb"><a>Home</a> › <a>Cards</a> › <a>梦境</a></nav>'
        assert bwd.breadcrumb_cat(html) == "梦境"
