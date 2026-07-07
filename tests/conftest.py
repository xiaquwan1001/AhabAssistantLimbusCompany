"""
Pytest configuration for AALC tests.
Mocks Windows-specific and game-specific dependencies.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to sys.path so 'utils', 'module', 'tasks' are importable
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ── Mock Windows-only modules before any test imports ──
mock_win32crypt = MagicMock()
sys.modules["win32crypt"] = mock_win32crypt

mock_cv2 = MagicMock()
sys.modules["cv2"] = mock_cv2

# ── Mock module.config.cfg ──
mock_cfg = MagicMock()
mock_cfg.set_win_size = 1080
mock_cfg.hard_mirror = False
mock_cfg.floor_3_exit = False
mock_cfg.save_rewards = False
mock_cfg.not_skip_whitegossypium = False
mock_cfg.last_auto_change = 0.0

mock_module_config = MagicMock()
mock_module_config.cfg = mock_cfg
sys.modules["module"] = MagicMock()
sys.modules["module.config"] = mock_module_config

# ── Mock module.logger ──
mock_log = MagicMock()
sys.modules["module.logger"] = MagicMock()
sys.modules["module.logger"].log = mock_log

# ── Mock module.automation ──
sys.modules["module.automation"] = MagicMock()
sys.modules["module.automation"].auto = MagicMock()

# ── Mock module.ocr ──
sys.modules["module.ocr"] = MagicMock()
sys.modules["module.ocr"].ocr = MagicMock()

# ── Mock module.decorator ──
sys.modules["module.decorator"] = MagicMock()
sys.modules["module.decorator.decorator"] = MagicMock()


def mock_begin_and_finish_time_log(task_name=""):
    """Stub decorator that returns the function unchanged."""
    def decorator(func):
        return func
    return decorator


sys.modules["module.decorator.decorator"].begin_and_finish_time_log = mock_begin_and_finish_time_log

# ── Mock module.my_error ──
sys.modules["module.my_error"] = MagicMock()
sys.modules["module.my_error.my_error"] = MagicMock()

# ── Mock tasks.* imports ──
sys.modules["tasks"] = MagicMock()
sys.modules["tasks.base"] = MagicMock()
sys.modules["tasks.base.retry"] = MagicMock()
sys.modules["tasks.base.back_init_menu"] = MagicMock()
sys.modules["tasks.base.make_enkephalin_module"] = MagicMock()
sys.modules["tasks.battle"] = MagicMock()
sys.modules["tasks.battle.battle"] = MagicMock()
sys.modules["tasks.event"] = MagicMock()
sys.modules["tasks.event.event_handling"] = MagicMock()
sys.modules["tasks.teams"] = MagicMock()
sys.modules["tasks.teams.team_formation"] = MagicMock()
sys.modules["tasks.mirror"] = MagicMock()
sys.modules["tasks.mirror.in_shop"] = MagicMock()
sys.modules["tasks.mirror.reward_card"] = MagicMock()
sys.modules["tasks.mirror.search_road"] = MagicMock()
sys.modules["tasks.mirror.select_theme_pack"] = MagicMock()

# ── Mock utils submodules (NOT utils itself - we need real imports) ──
sys.modules["utils.image_utils"] = MagicMock()
sys.modules["utils.path_manager"] = MagicMock()

# ── Mock PIL (available but keep consistent) ──
sys.modules["PIL"] = MagicMock()
