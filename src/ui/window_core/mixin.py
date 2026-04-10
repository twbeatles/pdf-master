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
    _choose_output_directory,
    _choose_save_file,
    _get_output_dialog_dir,
    _open_last_folder,
    _remember_output_location,
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
    _get_output_dialog_dir = _get_output_dialog_dir
    _remember_output_location = _remember_output_location
    _choose_save_file = _choose_save_file
    _choose_output_directory = _choose_output_directory
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
