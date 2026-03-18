import inspect


def test_worker_dispatch_registry_covers_public_worker_handlers():
    from src.core.worker import WorkerThread
    from src.core.worker_runtime.dispatch import MODE_TO_HANDLER

    public_handlers = set()
    for cls in WorkerThread.__mro__:
        if cls.__module__.startswith("src.core") and not cls.__module__.endswith("_typing"):
            for name, value in cls.__dict__.items():
                if name.startswith("_") or name in {"cancel", "run"}:
                    continue
                if inspect.isfunction(value):
                    public_handlers.add(name)

    assert set(MODE_TO_HANDLER.keys()) == set(MODE_TO_HANDLER.values())
    assert set(MODE_TO_HANDLER.values()) == public_handlers

    for mode, handler_name in MODE_TO_HANDLER.items():
        handler = getattr(WorkerThread, handler_name, None)
        assert callable(handler), f"Dispatch target for mode '{mode}' is not callable: {handler_name}"
