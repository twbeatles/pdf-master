from .menu import (
    _change_language,
    _create_menu_bar,
    _show_about,
    _show_help,
    _show_shortcuts,
    _update_recent_menu_bar,
)
from .shortcuts import _install_wheel_filters, _setup_shortcuts, _shortcut_open_file
from .state import (
    _open_last_folder,
    _restore_window_geometry,
    _save_settings_on_exit,
    _save_splitter_state,
)
from .theme import _apply_theme, _create_header, _toggle_theme
from .._typing import MainWindowHost


class MainWindowCoreMixin(MainWindowHost):
    _install_wheel_filters = _install_wheel_filters
    _setup_shortcuts = _setup_shortcuts
    _shortcut_open_file = _shortcut_open_file
    _open_last_folder = _open_last_folder
    _save_splitter_state = _save_splitter_state
    _restore_window_geometry = _restore_window_geometry
    _create_menu_bar = _create_menu_bar
    _change_language = _change_language
    _update_recent_menu_bar = _update_recent_menu_bar
    _show_shortcuts = _show_shortcuts
    _show_about = _show_about
    _create_header = _create_header
    _toggle_theme = _toggle_theme
    _apply_theme = _apply_theme
    _show_help = _show_help
    _save_settings_on_exit = _save_settings_on_exit
