import inspect


def test_worker_dispatch_registry_covers_public_worker_handlers():
    from src.core.worker import WorkerThread
    from src.core.worker_runtime.dispatch import MODE_TO_HANDLER, OPERATION_SPECS

    public_handlers = set()
    for cls in WorkerThread.__mro__:
        if cls.__module__.startswith("src.core") and not cls.__module__.endswith("_typing"):
            for name, value in cls.__dict__.items():
                if name.startswith("_") or name in {"cancel", "run"}:
                    continue
                if inspect.isfunction(value):
                    public_handlers.add(name)

    assert set(OPERATION_SPECS) == set(MODE_TO_HANDLER)
    assert {spec.handler for spec in OPERATION_SPECS.values()} == public_handlers

    for mode, handler_name in MODE_TO_HANDLER.items():
        spec = OPERATION_SPECS[mode]
        assert spec.mode == mode
        assert spec.handler == handler_name
        assert spec.title_key
        handler = getattr(WorkerThread, handler_name, None)
        assert callable(handler), f"Dispatch target for mode '{mode}' is not callable: {handler_name}"


def test_worker_dispatch_specs_expose_extended_metadata():
    from src.core.worker_runtime.dispatch import get_operation_spec

    compress = get_operation_spec("compress")
    assert compress is not None
    assert compress.refresh_preview is True
    assert compress.cancel_cleanup == "same_path_restore"
    assert compress.output_extensions == (".pdf",)

    markdown = get_operation_spec("extract_markdown")
    assert markdown is not None
    assert markdown.output_extensions == (".md",)
    assert markdown.cancel_cleanup == "created_outputs"

    ai_summary = get_operation_spec("ai_summarize")
    assert ai_summary is not None
    assert ai_summary.result_payload_keys == ("title", "summary", "key_points")
    assert ai_summary.refresh_preview is False

    batch = get_operation_spec("batch")
    assert batch is not None
    assert batch.required_kwargs == ("output_dir", "operation")
    assert batch.cancel_cleanup == "created_outputs"
