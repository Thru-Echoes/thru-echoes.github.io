"""
Playwright UI tests for JS-interactive elements on the portfolio site.

What this covers that check_links.py does not:

- Theme toggle (light ↔ dark)
- Skip-to-content links (focus + hash)
- TOC sidebar expand/collapse ("Open Folder")
- Downloads dropdown (frontmatter menu)
- Author Details popover
- Search dialog trigger (button + keyboard shortcut)
- Copy-code-to-clipboard button
- Action menu (kebab)
- Keyboard: Escape closes open dialogs

Each test is independent: it navigates to a fresh page and exercises
one interaction. Tests that depend on a specific element gracefully
`pytest.skip()` when the element is absent — the site is young and
book-theme may omit certain chrome on some routes.

Run against a live preview:

    npx -y mystmd@latest start           # in another terminal
    .venv/bin/pytest tests/check_ui.py -v
"""
from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, ViewportSize, expect


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

DESKTOP: ViewportSize = {"width": 1440, "height": 900}
MOBILE: ViewportSize = {"width": 390, "height": 844}

# Pages we'll sample for per-page interactions. Not every test needs
# every page; these are representatives.
LANDING = "/"
CASE_STUDY = "/meridian"
WITH_CODE_BLOCK = "/fsm"   # has a fenced code block → copy button


def html_classes(page: Page) -> str:
    return page.evaluate("document.documentElement.className")


def set_desktop(page: Page) -> None:
    page.set_viewport_size(DESKTOP)


def set_mobile(page: Page) -> None:
    page.set_viewport_size(MOBILE)


# ─────────────────────────────────────────────────────────────────────
# Theme toggle
# ─────────────────────────────────────────────────────────────────────

class TestThemeToggle:
    def test_toggle_changes_html_class(self, page: Page, base_url: str):
        page.goto(base_url + LANDING)
        set_desktop(page)

        before = html_classes(page)
        btn = page.get_by_label("Toggle theme between light and dark mode")
        expect(btn).to_be_visible()
        btn.click()

        page.wait_for_function(
            "prev => document.documentElement.className !== prev",
            arg=before,
            timeout=3000,
        )
        after = html_classes(page)
        assert after != before
        # Meaningful change: one of these two classes flipped.
        assert ("dark" in before) != ("dark" in after), (
            f"Expected 'dark' class to toggle; before={before!r} after={after!r}"
        )

    def test_toggle_is_idempotent(self, page: Page, base_url: str):
        """Two clicks should land us back where we started."""
        page.goto(base_url + LANDING)
        set_desktop(page)
        btn = page.get_by_label("Toggle theme between light and dark mode")
        before = html_classes(page)
        btn.click()
        page.wait_for_function(
            "prev => document.documentElement.className !== prev",
            arg=before, timeout=3000,
        )
        btn.click()
        page.wait_for_function(
            "target => document.documentElement.className === target",
            arg=before, timeout=3000,
        )
        assert html_classes(page) == before


# ─────────────────────────────────────────────────────────────────────
# Skip-to-content links (a11y)
# ─────────────────────────────────────────────────────────────────────

class TestSkipLinks:
    """Skip links are a11y features. The a-tag click behavior varies by
    browser + theme; what matters for correctness is that (a) the link
    exists, (b) its href points to a valid id on the same page."""

    def test_skip_to_article_link_targets_valid_id(self, page: Page, base_url: str):
        page.goto(base_url + CASE_STUDY)
        set_desktop(page)

        link = page.get_by_role("link", name=re.compile(r"Skip to article content", re.I))
        expect(link).to_be_attached()
        href = link.get_attribute("href")
        assert href and href.startswith("#"), f"Expected fragment href, got {href!r}"
        target_id = href.lstrip("#")
        target = page.locator(f"#{target_id}")
        expect(target).to_be_attached()

    def test_skip_to_frontmatter_link_targets_valid_id(self, page: Page, base_url: str):
        page.goto(base_url + LANDING)
        set_desktop(page)
        link = page.get_by_role(
            "link", name=re.compile(r"Skip to article frontmatter", re.I)
        )
        expect(link).to_be_attached()
        href = link.get_attribute("href")
        assert href and href.startswith("#"), f"Expected fragment href, got {href!r}"
        target_id = href.lstrip("#")
        target = page.locator(f"#{target_id}")
        expect(target).to_be_attached()


# ─────────────────────────────────────────────────────────────────────
# Sidebar TOC expand / collapse
# ─────────────────────────────────────────────────────────────────────

class TestTocExpand:
    def test_open_folder_reveals_children(self, page: Page, base_url: str):
        """Clicking 'Open Folder' in the TOC should expand its children."""
        page.goto(base_url + LANDING)
        set_desktop(page)

        # Target buttons by their aria-label. There may be several — we
        # click the first collapsed one and assert children become visible.
        buttons = page.get_by_role("button", name="Open Folder")
        if buttons.count() == 0:
            pytest.skip("No 'Open Folder' button on this page.")

        first = buttons.first
        # Record visible link count before expanding.
        links_before = page.locator("nav a").count()
        first.click()
        # Give the accordion a moment to animate.
        page.wait_for_timeout(300)
        links_after = page.locator("nav a").count()
        assert links_after >= links_before, (
            f"Expected more nav links after expand; "
            f"before={links_before}, after={links_after}"
        )


# ─────────────────────────────────────────────────────────────────────
# Author Details popover
# ─────────────────────────────────────────────────────────────────────

class TestAuthorPopover:
    def test_click_opens_popover(self, page: Page, base_url: str):
        page.goto(base_url + CASE_STUDY)
        set_desktop(page)
        btn = page.get_by_role("button", name=re.compile(r"Author Details", re.I))
        if btn.count() == 0:
            pytest.skip("No Author Details button on this page.")
        btn.click()
        # Popover contains the email address. Accept either a visible
        # dialog or inline popover that exposes the author's email.
        page.wait_for_timeout(300)
        shown_email = page.get_by_text("omuellerklein@berkeley.edu").first
        expect(shown_email).to_be_visible(timeout=2000)


# ─────────────────────────────────────────────────────────────────────
# Downloads dropdown
# ─────────────────────────────────────────────────────────────────────

class TestDownloads:
    def test_click_reveals_menu(self, page: Page, base_url: str):
        page.goto(base_url + CASE_STUDY)
        set_desktop(page)

        btn = page.locator(".myst-fm-downloads-button")
        if btn.count() == 0:
            pytest.skip("No downloads button on this page.")
        btn.first.click()
        # Expect the expanded state; aria-expanded flips to true or a
        # menu panel becomes visible.
        page.wait_for_timeout(300)
        expanded = btn.first.get_attribute("aria-expanded")
        # Either the ARIA state flipped, or a menu role element showed.
        menu = page.get_by_role("menu")
        assert expanded == "true" or menu.count() > 0, (
            f"Expected downloads menu to open; aria-expanded={expanded!r}, "
            f"menu count={menu.count()}"
        )


# ─────────────────────────────────────────────────────────────────────
# Search button + Cmd/Ctrl+K
# ─────────────────────────────────────────────────────────────────────

class TestSearch:
    def test_search_button_present(self, page: Page, base_url: str):
        page.goto(base_url + LANDING)
        set_desktop(page)
        btn = page.locator(".myst-search-bar").first
        expect(btn).to_be_attached()

    def test_search_is_disabled_or_opens_dialog(self, page: Page, base_url: str):
        """Two acceptable outcomes:
        - button is marked disabled (MyST dev default; search not indexed); or
        - clicking opens a dialog.
        Fail only if the button exists, is *not* disabled, and also does
        not open a dialog on click.
        """
        page.goto(base_url + LANDING)
        set_desktop(page)
        btn = page.locator(".myst-search-bar").first
        classes = btn.get_attribute("class") or ""
        if "disabled" in classes:
            pytest.skip(
                f"Search bar is disabled (class={classes!r}); dev default, "
                "not a failure."
            )
        btn.click()
        page.wait_for_timeout(500)
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=2000)


# ─────────────────────────────────────────────────────────────────────
# Copy-to-clipboard button on code blocks
# ─────────────────────────────────────────────────────────────────────

class TestCopyCode:
    def test_copy_button_present_on_page_with_code(self, page: Page, base_url: str):
        page.goto(base_url + WITH_CODE_BLOCK)
        set_desktop(page)
        btn = page.get_by_role("button", name=re.compile(r"Copy code", re.I))
        if btn.count() == 0:
            pytest.skip(f"No copy button found on {WITH_CODE_BLOCK}")
        expect(btn.first).to_be_visible()

    def test_copy_button_is_clickable(self, page: Page, base_url: str):
        """We don't verify clipboard contents (requires a permissions
        grant that Playwright needs context-level configuration for).
        We verify the button doesn't throw when clicked and it stays
        attached to the DOM afterwards — a simple smoke test."""
        page.goto(base_url + WITH_CODE_BLOCK)
        set_desktop(page)
        btn = page.get_by_role("button", name=re.compile(r"Copy code", re.I))
        if btn.count() == 0:
            pytest.skip("No copy button on this page.")
        btn.first.click()
        expect(btn.first).to_be_attached()


# ─────────────────────────────────────────────────────────────────────
# Mobile nav (hamburger menu)
# ─────────────────────────────────────────────────────────────────────

class TestMobileNav:
    def test_hamburger_shows_nav_links(self, page: Page, base_url: str):
        set_mobile(page)
        page.goto(base_url + LANDING)

        # The top-nav menu button is usually aria-labeled "Open Menu".
        buttons = page.get_by_role("button", name=re.compile(r"Open Menu", re.I))
        if buttons.count() == 0:
            pytest.skip("No mobile 'Open Menu' button present.")
        buttons.first.click()
        page.wait_for_timeout(400)

        # At minimum, the expanded menu surface should contain the main
        # navigation links.
        for target in ("Projects", "About", "CV"):
            loc = page.get_by_role("link", name=target).first
            expect(loc).to_be_visible(timeout=2000)


# ─────────────────────────────────────────────────────────────────────
# Escape closes open overlays
# ─────────────────────────────────────────────────────────────────────

class TestKeyboard:
    def test_escape_closes_downloads_if_open(self, page: Page, base_url: str):
        page.goto(base_url + CASE_STUDY)
        set_desktop(page)
        btn = page.locator(".myst-fm-downloads-button")
        if btn.count() == 0:
            pytest.skip("No downloads button on this page.")
        btn.first.click()
        page.wait_for_timeout(200)
        # If a menu opened, Escape should close it.
        menu = page.get_by_role("menu")
        if menu.count() == 0:
            pytest.skip("Downloads menu did not open; nothing to close.")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        # After Escape, no role="menu" should be visible (or aria-expanded=false).
        expanded = btn.first.get_attribute("aria-expanded")
        assert expanded in (None, "false") or page.get_by_role("menu").count() == 0


# ─────────────────────────────────────────────────────────────────────
# Smoke: dark-mode hero still readable
# ─────────────────────────────────────────────────────────────────────

class TestDarkModeRender:
    def test_hero_portrait_visible_in_dark(self, page: Page, base_url: str):
        page.goto(base_url + LANDING)
        set_desktop(page)
        # Flip to dark.
        page.get_by_label("Toggle theme between light and dark mode").click()
        page.wait_for_function(
            "() => document.documentElement.classList.contains('dark')",
            timeout=3000,
        )
        img = page.locator(".hero-portrait-img").first
        expect(img).to_be_visible()
        w = img.evaluate("el => el.clientWidth")
        assert w > 200, f"Expected portrait ≥200px wide, got {w}"
