"""
Test new-style game handlers: DismissPromptHandler, CloseInfinityHandler.
Pure unit tests — mock AutomationPort, no Win32 deps.
"""

from unittest.mock import MagicMock, patch

import pytest

from module4_decision_layer.handlers.game import (
    CloseInfinityHandler,
    DismissPromptHandler,
    EgoGiftConfirmHandler,
    EnterNodeHandler,
    EventEffectHandler,
    EventHandler,
    InitEgoGiftHandler,
    NoTeamHandler,
    ObserveEgoGiftHandler,
    RewardCardHandler,
    StarlightHandler,
    TeamSelectHandler,
)


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


class TestEgoGiftConfirmHandler:
    def make_handler(self, auto=None):
        return EgoGiftConfirmHandler(auto=auto)

    def test_confirms_when_click_succeeds(self):
        auto = MagicMock()
        auto.click_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto)
        result = handler()
        assert result is True
        auto.click_element.assert_called_once_with("mirror/road_in_mir/ego_gift_get_confirm_assets.png")

    def test_returns_false_when_click_fails(self):
        auto = MagicMock()
        auto.click_element.return_value = False
        handler = self.make_handler(auto)
        result = handler()
        assert result is False
        auto.click_element.assert_called_once_with("mirror/road_in_mir/ego_gift_get_confirm_assets.png")

    def test_raises_without_auto(self):
        handler = self.make_handler(auto=None)
        with pytest.raises(ValueError, match="requires 'auto'"):
            handler()

    def test_accepts_auto_at_call_time(self):
        auto = MagicMock()
        auto.click_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto=None)
        result = handler(auto=auto)
        assert result is True
        auto.click_element.assert_called_once_with("mirror/road_in_mir/ego_gift_get_confirm_assets.png")


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


class TestEnterNodeHandler:
    def make_handler(self, auto=None):
        return EnterNodeHandler(auto=auto)

    def test_enters_when_click_succeeds(self):
        auto = MagicMock()
        auto.click_element.return_value = True
        handler = self.make_handler(auto)
        result = handler()
        assert result is True
        auto.click_element.assert_called_once_with("mirror/road_in_mir/enter_assets.png")

    def test_returns_false_when_click_fails(self):
        auto = MagicMock()
        auto.click_element.return_value = False
        handler = self.make_handler(auto)
        result = handler()
        assert result is False
        auto.click_element.assert_called_once_with("mirror/road_in_mir/enter_assets.png")

    def test_raises_without_auto(self):
        handler = self.make_handler(auto=None)
        with pytest.raises(ValueError, match="requires 'auto'"):
            handler()

    def test_accepts_auto_at_call_time(self):
        auto = MagicMock()
        auto.click_element.return_value = True
        handler = self.make_handler(auto=None)  # no constructor auto
        result = handler(auto=auto)
        assert result is True
        auto.click_element.assert_called_once_with("mirror/road_in_mir/enter_assets.png")


class TestEventEffectHandler:
    def make_handler(self, auto=None):
        return EventEffectHandler(auto=auto)

    def test_selects_when_button_found(self):
        auto = MagicMock()
        # first call (button) returns True, second call (confirm) returns True
        auto.click_element.side_effect = [True, True]
        handler = self.make_handler(auto)
        result = handler()
        assert result is True
        assert auto.click_element.call_count == 2
        auto.click_element.assert_any_call(
            "mirror/road_in_mir/event_effect_button.png", threshold=0.75
        )
        auto.click_element.assert_any_call(
            "mirror/road_in_mir/select_event_effect_confirm.png"
        )

    def test_returns_false_when_button_missing(self):
        auto = MagicMock()
        auto.click_element.return_value = False
        handler = self.make_handler(auto)
        result = handler()
        assert result is False
        auto.click_element.assert_called_once_with(
            "mirror/road_in_mir/event_effect_button.png", threshold=0.75
        )
        # confirm should NOT have been called
        assert [
            c for c in auto.click_element.call_args_list
            if c == (("mirror/road_in_mir/select_event_effect_confirm.png",), {})
        ] == []

    def test_raises_without_auto(self):
        handler = self.make_handler(auto=None)
        with pytest.raises(ValueError, match="requires 'auto'"):
            handler()

    def test_accepts_auto_at_call_time(self):
        auto = MagicMock()
        auto.click_element.side_effect = [True, True]
        handler = self.make_handler(auto=None)  # no constructor auto
        result = handler(auto=auto)
        assert result is True
        assert auto.click_element.call_count == 2


class TestEventHandler:
    def make_handler(self, auto=None):
        return EventHandler(auto=auto)

    def test_skips_when_skip_found(self):
        auto = MagicMock()
        auto.click_element.return_value = True
        handler = self.make_handler(auto)
        result = handler()
        assert result is True
        auto.click_element.assert_called_once_with("event/skip_assets.png", times=6)

    def test_does_nothing_when_no_skip(self):
        auto = MagicMock()
        auto.click_element.return_value = False
        handler = self.make_handler(auto)
        result = handler()
        assert result is False
        auto.click_element.assert_called_once_with("event/skip_assets.png", times=6)

    def test_raises_without_auto(self):
        handler = self.make_handler(auto=None)
        with pytest.raises(ValueError, match="requires 'auto'"):
            handler()

    def test_accepts_auto_at_call_time(self):
        auto = MagicMock()
        auto.click_element.return_value = True
        handler = self.make_handler(auto=None)  # no constructor auto
        result = handler(auto=auto)
        assert result is True
        auto.click_element.assert_called_once_with("event/skip_assets.png", times=6)


class TestNoTeamHandler:
    def make_handler(self, auto=None):
        return NoTeamHandler(auto=auto)

    def test_resets_when_no_team(self):
        auto = MagicMock()
        auto.find_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto)
        result = handler()
        assert result is True
        auto.find_element.assert_called_once_with("battle/select_none_assets.png")
        auto.mouse_click_blank.assert_called_once_with()

    def test_does_nothing_when_team_ok(self):
        auto = MagicMock()
        auto.find_element.return_value = None
        handler = self.make_handler(auto)
        result = handler()
        assert result is False
        auto.find_element.assert_called_once_with("battle/select_none_assets.png")
        auto.mouse_click_blank.assert_not_called()

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
        auto.find_element.assert_called_once_with("battle/select_none_assets.png")
        auto.mouse_click_blank.assert_called_once_with()


class TestRewardCardHandler:
    """Handler for Mirror._run_reward_card migration."""

    ASSET = "mirror/road_in_mir/select_encounter_reward_card_assets.png"

    def make_handler(self, auto=None, reward_cards_select=None):
        return RewardCardHandler(auto=auto, reward_cards_select=reward_cards_select)

    @pytest.fixture
    def mock_reward_card_module(self):
        """Mock tasks.mirror.reward_card so the lazy import succeeds."""
        import sys
        mock_module = MagicMock()
        mock_module.get_reward_card = MagicMock()
        with patch.dict(sys.modules, {"tasks.mirror.reward_card": mock_module}):
            yield mock_module

    def test_selects_card_with_custom_select(self, mock_reward_card_module):
        """find returns coords, handler gets reward_cards_select param → calls get_reward_card(select)."""
        auto = MagicMock()
        auto.find_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto=None, reward_cards_select=2)
        result = handler(auto=auto)
        assert result is True
        mock_reward_card_module.get_reward_card.assert_called_once_with(2)

    def test_selects_card_without_custom(self, mock_reward_card_module):
        """find returns coords, handler omits reward_cards_select → calls get_reward_card()."""
        auto = MagicMock()
        auto.find_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto=None)  # no reward_cards_select
        result = handler(auto=auto)
        assert result is True
        mock_reward_card_module.get_reward_card.assert_called_once_with()

    def test_does_nothing_when_no_card(self):
        """find returns None → handler returns False."""
        auto = MagicMock()
        auto.find_element.return_value = None
        handler = self.make_handler(auto=auto)
        result = handler()
        assert result is False

    def test_raises_without_auto(self):
        handler = self.make_handler(auto=None)
        with pytest.raises(ValueError, match="requires 'auto'"):
            handler()

    def test_accepts_auto_at_call_time(self, mock_reward_card_module):
        auto = MagicMock()
        auto.find_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto=None, reward_cards_select=3)
        result = handler(auto=auto)
        assert result is True
        mock_reward_card_module.get_reward_card.assert_called_once_with(3)


class TestObserveEgoGiftHandler:
    BLEED_ASSET = "mirror/road_to_mir/observe_ego_gift/observe_bleed_assets.png"
    BURN_ASSET = "mirror/road_to_mir/observe_ego_gift/observe_burn_assets.png"

    def make_handler(self, auto=None):
        return ObserveEgoGiftHandler(auto=auto)

    def test_found_when_bleed(self):
        """find bleed returns coords, burn returns None → True"""
        auto = MagicMock()
        auto.find_element.side_effect = lambda target, **kw: (
            [100, 100, 200, 200] if target == self.BLEED_ASSET else None
        )
        handler = self.make_handler(auto)
        result = handler()
        assert result is True

    def test_found_when_burn(self):
        """find bleed returns None, burn returns coords → True"""
        auto = MagicMock()
        auto.find_element.side_effect = lambda target, **kw: (
            [100, 100, 200, 200] if target == self.BURN_ASSET else None
        )
        handler = self.make_handler(auto)
        result = handler()
        assert result is True

    def test_missing_when_neither(self):
        """both None → False"""
        auto = MagicMock()
        auto.find_element.return_value = None
        handler = self.make_handler(auto)
        result = handler()
        assert result is False

    def test_raises_without_auto(self):
        handler = self.make_handler(auto=None)
        with pytest.raises(ValueError, match="requires 'auto'"):
            handler()

    def test_call_time_auto(self):
        auto = MagicMock()
        auto.find_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto=None)
        result = handler(auto=auto)
        assert result is True
        auto.find_element.assert_any_call(self.BLEED_ASSET, model="clam")


class TestTeamSelectHandler:
    ASSET = "mirror/road_to_mir/select_team_stars_assets.png"

    def make_handler(self, auto=None):
        return TeamSelectHandler(auto=auto)

    def test_select_found(self):
        """find returns coords → True"""
        auto = MagicMock()
        auto.find_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto)
        result = handler()
        assert result is True
        auto.find_element.assert_called_once_with(self.ASSET)

    def test_select_missing(self):
        """find returns None → False"""
        auto = MagicMock()
        auto.find_element.return_value = None
        handler = self.make_handler(auto)
        result = handler()
        assert result is False
        auto.find_element.assert_called_once_with(self.ASSET)

    def test_raises_without_auto(self):
        handler = self.make_handler(auto=None)
        with pytest.raises(ValueError, match="requires 'auto'"):
            handler()

    def test_call_time_auto(self):
        auto = MagicMock()
        auto.find_element.return_value = [100, 100, 200, 200]
        handler = self.make_handler(auto=None)
        result = handler(auto=auto)
        assert result is True
        auto.find_element.assert_called_once_with(self.ASSET)
