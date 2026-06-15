"""Credential and model-tab action mixins for the desktop surface."""

from __future__ import annotations

from .. import credentials
from ..debug_host import available_descriptors
from . import credentials_rendering, dialogs, model_catalog_actions, repository


class OrchestratorAppCredentialActions:
    def _refresh_credentials_view(self) -> None:
        self._credentials_profile = credentials.resolve_credentials(self._state_dir)
        self._credentials_state = credentials.load_credentials_state(self._state_dir)
        credentials_rendering.apply_credentials_view(self)

    def _initialize_credentials_tab(self) -> None:
        self._refresh_credentials_view()

    def _initialize_model_settings_tab(self) -> None:
        self._restore_runtime_settings()
        if hasattr(self, "_runtime_settings_widgets"):
            model_catalog_actions.render_model_catalog(self)

    def _initialize_debug_tab(self) -> None:
        if not getattr(self, "_debug_descriptors", {}):
            self._debug_descriptors = available_descriptors(registry_path=self._project_root / "module-registry.json")
        self._restore_debug_state()

    def _on_credentials_mode_change(self, value: str) -> None:
        state = credentials.load_credentials_state(self._state_dir)
        state.auth_mode = "oauth" if str(value).strip().lower() == "oauth" else "api_keys"
        credentials.save_credentials_state(self._state_dir, state)
        self._refresh_credentials_view()

    def _save_credentials_target(self, target: str) -> None:
        try:
            if hasattr(self, "_flush_pending_save"):
                self._flush_pending_save("runtime_settings")
            value = self._credential_widgets[target]["entry"].get().strip()
            credentials.save_api_key(
                self._state_dir,
                target,
                value,
                provider_settings=_provider_settings_for_credentials_target(self, target),
            )
            self._credential_widgets[target]["entry"].delete(0, "end")
            self._refresh_credentials_view()
        except Exception as exc:
            self._append_log(f"[ERROR] Saving credentials failed: {exc}")
            dialogs.show_error(str(exc))

    def _delete_credentials_target(self, target: str) -> None:
        try:
            if hasattr(self, "_flush_pending_save"):
                self._flush_pending_save("runtime_settings")
            credentials.delete_api_key(
                self._state_dir,
                target,
                provider_settings=_provider_settings_for_credentials_target(self, target),
            )
            self._credential_widgets[target]["entry"].delete(0, "end")
            self._refresh_credentials_view()
        except Exception as exc:
            self._append_log(f"[ERROR] Deleting credentials failed: {exc}")
            dialogs.show_error(str(exc))

    def _login_oauth(self) -> None:
        try:
            credentials.login_with_oauth(self._state_dir)
            self._refresh_credentials_view()
        except Exception as exc:
            self._append_log(f"[ERROR] OAuth login failed: {exc}")
            dialogs.show_error(str(exc))

    def _logout_oauth(self) -> None:
        try:
            credentials.logout_from_oauth(self._state_dir)
            self._refresh_credentials_view()
        except Exception as exc:
            self._append_log(f"[ERROR] OAuth logout failed: {exc}")
            dialogs.show_error(str(exc))


def _provider_settings_for_credentials_target(app, target: str):
    try:
        runtime_settings = repository.current_runtime_settings(app)
    except Exception:
        runtime_settings = getattr(app, "_runtime_settings", repository.default_runtime_settings())
    return runtime_settings.provider_settings_for_target(target)
