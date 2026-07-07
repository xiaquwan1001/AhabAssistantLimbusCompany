"""
Test new-style game handlers: DismissPromptHandler, CloseInfinityHandler.
Pure unit tests — mock AutomationPort, no Win32 deps.
"""

from unittest.mock import MagicMock

import pytest

from module4_decision_layer.handlers.game import CloseInfinityHandler, DismissPromptHandler


class TestDismissPromptHandler:
    def make_handler(self, auto=None):
        return DismissPromptHandler(auto=auto)

    def test_dismisses_when_prompt_and_back_found(self):
        auto = MagicMock()
        auto.find_element.side_effect = lambda target, **kw: (
            [100, 100, 200, 200] if target in [
                "home/first_prompt_assets.png",
                "home/back_assets.png",
            ] else None
        )
        handler = self.make_handler(auto)
        result = handler()
        assert result is True
        auto.click_element.assert_called_once_with("home/back_assets.png")

    def test_does_nothing_if_no_prompt(self):
        auto = MagicMock()
        auto.find_element.return_value = None
        handler = self.make_handler(auto)
        result = handler()
        assert result is False
        auto.click_element.assert_not_called()

    def test_does_nothing_if_no_back_button(self):
        auto = MagicMock()
        # first_prompt found, but back_assets not found
        auto.find_element.side_effect = lambda target, **kw: (
            [100, 100, 200, 200] if target == "home/first_prompt_assets.png" else None
        )
        handler = self.make_handler(auto)
        result = handler()
        assert result is False
        auto.click_element.assert_not_called()

    def test_uses_correct_model_on_find(self):
        auto = MagicMock()
        auto.find_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto)
        handler()
        # first_prompt uses clam, back_assets uses normal
        calls = auto.find_element.call_args_list
        assert calls[0] == (("home/first_prompt_assets.png",), {"model": "clam"})
        assert calls[1] == (("home/back_assets.png",), {"model": "normal"})

    def test_raises_without_auto(self):
        handler = self.make_handler(auto=None)
        with pytest.raises(ValueError, match="requires 'auto'"):
            handler()

    def test_accepts_auto_at_call_time(self):
        auto = MagicMock()
        auto.find_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto=None)  # no constructor auto
        result = handler(auto=auto)
        assert result is True
        auto.click_element.assert_called_once()


class TestCloseInfinityHandler:
    def make_handler(self, auto=None):
        return CloseInfinityHandler(auto=auto)

    def test_closes_when_infinity_found(self):
        auto = MagicMock()
        auto.find_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto)
        result = handler()
        assert result is True
        auto.find_element.assert_called_once_with("mirror/infinity_mirror_assets.png")
        auto.click_element.assert_called_once_with("mirror/infinity_mirror_close_assets.png")

    def test_does_nothing_if_no_infinity(self):
        auto = MagicMock()
        auto.find_element.return_value = None
        handler = self.make_handler(auto)
        result = handler()
        assert result is False
        auto.click_element.assert_not_called()

    def test_raises_without_auto(self):
        handler = self.make_handler(auto=None)
        with pytest.raises(ValueError, match="requires 'auto'"):
            handler()

    def test_accepts_auto_at_call_time(self):
        auto = MagicMock()
        auto.find_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto=None)
        result = handler(auto=auto)
        assert result is True
        auto.click_element.assert_called_once()
