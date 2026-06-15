from processor_test_shared import *


class ProcessSingleOutputCases:
    def test_process_single_uses_hash_suffix_for_existing_output_name(self, processing_env, tmp_path):
        env = processing_env
        out_dir = tmp_path / "single_output"
        out_dir.mkdir()

        first = tmp_path / "a" / "same.txt"
        second = tmp_path / "b" / "same.txt"
        first.parent.mkdir()
        second.parent.mkdir()
        first.write_text("alpha", encoding="utf-8")
        second.write_text("beta", encoding="utf-8")

        proc = Processor(
            env["config"],
            env["plugin_mgr"],
        )
        proc.process_single(first, write_output=True, output_dir=out_dir)
        proc.process_single(second, write_output=True, output_dir=out_dir)

        raw_names = {path.name for path in (out_dir / "raw_extracts").glob("*.raw.json")}
        assert len(raw_names) == 2
        assert "same.txt.raw.json" in raw_names
        assert any(name.startswith("same.txt.") and name != "same.txt.raw.json" for name in raw_names)

    def test_process_single_uses_child_run_directory_when_output_is_active(self, processing_env, tmp_path):
        env = processing_env
        test_file = tmp_path / "data.txt"
        test_file.write_text("Test data", encoding="utf-8")
        out_dir = tmp_path / "single_output"
        out_dir.mkdir()
        _mark_output_active(out_dir)

        proc = Processor(
            env["config"],
            env["plugin_mgr"],
        )
        extracts = proc.process_single(test_file, write_output=True, output_dir=out_dir)

        assert len(extracts) == 1
        run_dirs = list((out_dir / "runs").iterdir())
        assert len(run_dirs) == 1
        effective_output = run_dirs[0]
        assert len(list((effective_output / "raw_extracts").glob("*.raw.json"))) == 1
        assert not (out_dir / "raw_extracts").exists()

    def test_process_single_dry_run(self, processing_env, tmp_path):
        env = processing_env
        test_file = tmp_path / "dry.txt"
        test_file.write_text("Dry run", encoding="utf-8")

        proc = Processor(env["config"], env["plugin_mgr"])
        extracts = proc.process_single(test_file, write_output=False)
        assert len(extracts) == 1
        # Kein Output geschrieben
        assert not (tmp_path / "raw_extracts").exists()

    def test_process_single_to_dict(self, processing_env, tmp_path):
        env = processing_env
        test_file = tmp_path / "dict_test.txt"
        test_file.write_text("For to_dict", encoding="utf-8")

        proc = Processor(env["config"], env["plugin_mgr"])
        extracts = proc.process_single(test_file, write_output=False)
        d = extracts[0].to_dict()
        assert isinstance(d, dict)
        assert d["source"]["file_name"] == "dict_test.txt"
