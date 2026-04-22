def _focus_preview_search(self) -> None:
    if not getattr(self, "_current_preview_path", ""):
        return
    if getattr(self, "_preview_total_pages", 0) <= 0:
        return
    self.preview_image.set_search_panel_visible(True)
    self.preview_image.focus_search_input(select_all=True)


def _on_preview_search_visibility_changed(self, visible: bool) -> None:
    settings = getattr(self, "settings", None)
    if isinstance(settings, dict):
        settings["preview_search_expanded"] = bool(visible)
        if hasattr(self, "_schedule_settings_save"):
            self._schedule_settings_save()
