from processor_test_shared import *


class ProcessSingleErrorCases:
    def test_process_single_file_not_found(self, processing_env):
        env = processing_env
        proc = Processor(env["config"], env["plugin_mgr"])
        with pytest.raises(InputFileNotFoundError):
            proc.process_single("/nonexistent/file.txt", write_output=False)

    def test_process_single_file_too_large(self, processing_env, tmp_path):
        env = processing_env
        big_file = tmp_path / "big.txt"
        big_file.write_text("X" * 100, encoding="utf-8")

        config = IngestionConfig(max_file_size_mb=0)  # 0 MB = alles zu gross
        proc = Processor(config, env["plugin_mgr"])
        with pytest.raises(FileTooLargeError):
            proc.process_single(big_file, write_output=False)

    def test_process_single_unsupported_format(self, processing_env, tmp_path):
        env = processing_env
        unknown_file = tmp_path / "data.xyz"
        unknown_file.write_text("data", encoding="utf-8")

        proc = Processor(env["config"], env["plugin_mgr"])
        with pytest.raises(UnsupportedFormatError):
            proc.process_single(unknown_file, write_output=False)

    def test_process_single_plugin_exception_is_wrapped_as_plugin_error(self, processing_env, tmp_path):
        env = processing_env
        source = tmp_path / "boom.txt"
        source.write_text("boom", encoding="utf-8")

        class ExplodingPluginManager:
            def get_plugin_for_format(self, ext):
                return "text-plugin" if ext == ".txt" else None

            def invoke(self, _plugin_name, _file_path, config_override=None):
                del config_override
                raise RuntimeError("plugin exploded")

            def get_manifest(self, _plugin_name):
                return SimpleNamespace(version="1.0.0", capabilities=["text"])

            def shutdown_workers(self):
                return None

            def kill_all(self):
                return None

        proc = Processor(
            env["config"], ExplodingPluginManager(),
        )

        with pytest.raises(PluginError, match="plugin exploded") as exc_info:
            proc.process_single(source, write_output=False)

        assert "Plugin 'text-plugin'" in str(exc_info.value)

    def test_process_single_required_llm_ocr_without_output_dir_raises_value_error(self, processing_env, tmp_path):
        env = processing_env
        source = tmp_path / "needs-ocr.txt"
        source.write_text("ocr please", encoding="utf-8")

        class NeedsOcrPluginManager:
            def get_plugin_for_format(self, ext):
                return "text-plugin" if ext == ".txt" else None

            def invoke(self, _plugin_name, _file_path, config_override=None):
                del config_override
                return ExtractResult(
                    status="success",
                    blocks=_text_blocks("needs ocr"),
                    metadata={},
                    errors=[],
                    processing_time_ms=1,
                    needs_ocr=True,
                )

            def get_manifest(self, _plugin_name):
                return SimpleNamespace(version="1.0.0", capabilities=["text"])

            def shutdown_workers(self):
                return None

            def kill_all(self):
                return None

        proc = Processor(
            env["config"], NeedsOcrPluginManager(),
        )

        with pytest.raises(ValueError, match="Vision-Dokumente erfordern"):
            proc.process_single(source, write_output=False)
