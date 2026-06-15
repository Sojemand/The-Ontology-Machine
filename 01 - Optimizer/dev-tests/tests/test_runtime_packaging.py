from __future__ import annotations

import json

from packaging_contract_support import CHECK_RUNTIME, MODULE_MANIFEST, MODULE_ROOT, RUNTIME_MANIFEST, RUNTIME_PYTHON, RUNTIME_ROOT, run_batch, run_command


def test_bundled_runtime_provenance_is_self_contained():
    manifest = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    completed = run_command(
        [
            str(RUNTIME_PYTHON),
            "-c",
            (
                "import bs4, docx, encodings, extract_msg, fitz, json, odf, olefile, oletools, pdfplumber, striprtf, sys, yaml; "
                "from pathlib import Path; "
                "import RTFDE; "
                "import PIL; "
                "print(json.dumps({'version': sys.version.split()[0], "
                "'encodings': encodings.__file__, "
                "'bs4': str(Path(bs4.__file__).resolve()), "
                "'docx': str(Path(docx.__file__).resolve()), "
                "'extract_msg': str(Path(extract_msg.__file__).resolve()), "
                "'fitz': str(Path(fitz.__file__).resolve()), "
                "'odf': str(Path(odf.__file__).resolve()), "
                "'olefile': str(Path(olefile.__file__).resolve()), "
                "'oletools': str(Path(oletools.__file__).resolve()), "
                "'pdfplumber': str(Path(pdfplumber.__file__).resolve()), "
                "'pil': str(Path(PIL.__file__).resolve()), "
                "'rtfde': str(Path(RTFDE.__file__).resolve()), "
                "'striprtf': str(Path(striprtf.__file__).resolve()), "
                "'yaml': str(Path(yaml.__file__).resolve())}))"
            ),
        ],
        cwd=MODULE_ROOT,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    runtime_root = str(RUNTIME_ROOT.resolve()).lower()
    assert payload["version"].startswith(manifest["python_version"])
    assert payload["encodings"].lower().startswith(runtime_root)
    assert payload["bs4"].lower().startswith(runtime_root)
    assert payload["docx"].lower().startswith(runtime_root)
    assert payload["extract_msg"].lower().startswith(runtime_root)
    assert payload["fitz"].lower().startswith(runtime_root)
    assert payload["odf"].lower().startswith(runtime_root)
    assert payload["olefile"].lower().startswith(runtime_root)
    assert payload["oletools"].lower().startswith(runtime_root)
    assert payload["pdfplumber"].lower().startswith(runtime_root)
    assert payload["pil"].lower().startswith(runtime_root)
    assert payload["rtfde"].lower().startswith(runtime_root)
    assert payload["striprtf"].lower().startswith(runtime_root)
    assert payload["yaml"].lower().startswith(runtime_root)


def test_runtime_checker_reports_portable_runtime():
    completed = run_batch(CHECK_RUNTIME, cwd=MODULE_ROOT)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["python"]["path"].lower().endswith("runtime\\python\\python.exe")
    assert payload["provenance"]["encodings"].lower().startswith(str(RUNTIME_ROOT.resolve()).lower())
    assert payload["provenance"]["yaml"].lower().startswith(str(RUNTIME_ROOT.resolve()).lower())
    assert payload["provenance"]["optimizer_contract"].lower().startswith(str(MODULE_ROOT.resolve()).lower())
    assert payload["provenance"]["optimizer_file_contract"].lower().startswith(str(MODULE_ROOT.resolve()).lower())


def test_manifest_keeps_launcher_and_contract_surface_aligned():
    manifest = json.loads(MODULE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["launcher_module"] == "ingestion_layer_vision"
    assert manifest["contract_module"] == "ingestion_layer_vision.orchestrator_contract"
    assert manifest["actions"] == ["classify_document", "extract_document", "healthcheck", "scan_debug_input", "debug_run"]
    assert manifest["profiles"] == {
        "public_slot": "optimizer",
        "selector_field": "optimizer_profile",
        "default_profile": "vision",
        "internal_profiles": {
            "vision": {
                "package": "ingestion_layer_vision",
                "runtime_policy_path": "required",
                "role": "scan_image_ocr_profile",
            },
            "file": {
                "package": "ingestion_layer_file",
                "runtime_policy_path": "not_required",
                "role": "born_digital_file_profile",
            },
        },
        "routing": {
            "classify_document": "public_profile_gate",
            "extract_document": "selector_field",
            "healthcheck": "profile_aware",
            "scan_debug_input": "selector_field",
            "debug_run": "selector_field",
        },
    }
    assert manifest["debug_surface"] == {
        "supports_batch": True,
        "supports_single": True,
        "supports_scan": True,
        "input_source": "orchestrator_main_input",
        "output_source": "orchestrator_assigned_output",
        "controls": ["mode", "filters", "worker_count", "hash_tools"],
        "artifacts": ["raw_extracts", "page_assets"],
    }
    assert manifest["external_dependencies"] == [
        {
            "name": "optimizer_ocr",
            "kind": "llm",
            "required": False,
            "detail": "Vision-Profil: zentraler LLM-OCR-Port fuer gerenderte Page-Assets; Credentials und Provider werden ausschliesslich durch das Orchestrator-Ziel optimizer_ocr injiziert.",
        },
        {
            "name": "microsoft_outlook_desktop",
            "kind": "native",
            "required": False,
            "detail": "File-Profil: optional nur fuer COM-Fallback von .pst/.ost; bevorzugt ueber die gebuendelte mail-outlook-store-Runtime mit pypff. .msg/.oft/.eml/.emlx/.mbox laufen lokal in runtime/python.",
        },
    ]


def test_runtime_manifest_tracks_package_surface():
    manifest = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    assert "optimizer_ocr/__init__.py" in manifest["required_files"]
    assert "optimizer_ocr/workflow.py" in manifest["required_files"]
    assert "config/optimizer_ocr_prompt.md" in manifest["required_files"]
    assert "ingestion_layer_vision/paths/__init__.py" in manifest["required_files"]
    assert "ingestion_layer_vision/edit_contract/__main__.py" in manifest["required_files"]
    assert "ingestion_layer_vision/edit_contract/prompt_repository.py" in manifest["required_files"]
    assert "ingestion_layer_vision/edit_contract/workflow.py" in manifest["required_files"]
    assert "ingestion_layer_vision/orchestrator_contract/__main__.py" in manifest["required_files"]
    assert "ingestion_layer_vision/orchestrator_contract/classification_routing.py" in manifest["required_files"]
    assert "ingestion_layer_vision/orchestrator_contract/debug_errors.py" in manifest["required_files"]
    assert "ingestion_layer_vision/orchestrator_contract/debug_processing.py" in manifest["required_files"]
    assert "ingestion_layer_vision/orchestrator_contract/debug_support.py" in manifest["required_files"]
    assert "ingestion_layer_vision/orchestrator_contract/healthcheck_routing.py" in manifest["required_files"]
    assert "ingestion_layer_vision/orchestrator_contract/healthcheck_workflow.py" in manifest["required_files"]
    assert "ingestion_layer_file/orchestrator_contract/__init__.py" in manifest["required_files"]
    assert "ingestion_layer_file/orchestrator_contract/workflow.py" in manifest["required_files"]
    assert "ingestion_layer_vision/runtime_policy/__init__.py" in manifest["required_files"]
    assert "ingestion_layer_vision/runtime_policy/resolution.py" in manifest["required_files"]
    assert "ingestion_layer_vision/runtime_policy/validation.py" in manifest["required_files"]
    assert "ingestion_layer_vision/__main__.py" not in manifest["required_files"]
    assert "ingestion_layer_vision/main/__init__.py" not in manifest["required_files"]
    assert "run.bat" not in manifest["required_files"]
