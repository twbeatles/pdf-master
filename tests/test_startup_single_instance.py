"""단일 인스턴스 가드 + 시작 스플래시 회귀 테스트.

- 두 번째 인스턴스는 새 창을 띄우지 않고 종료해야 한다(중복 실행 pile-up 방지).
- 크래시 잔해(stale lock)는 다음 실행이 회수해야 한다.
"""
import os
import subprocess
import sys
import time

from _deps import require_pyqt6

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _import_main():
    require_pyqt6()
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    import main

    return main


def test_second_acquire_fails_while_first_holds(tmp_path):
    main = _import_main()
    lock_path = str(tmp_path / "single_instance.lock")

    acquired_first, first_lock = main.try_acquire_single_instance(lock_path)
    assert acquired_first is True
    assert first_lock is not None
    assert first_lock.staleLockTime() == 0
    try:
        # Long-running instances must remain exclusive past Qt's default 30s.
        old_time = time.time() - 120
        os.utime(lock_path, (old_time, old_time))
        acquired_second, second_lock = main.try_acquire_single_instance(lock_path)
        assert acquired_second is False
        assert second_lock is None
    finally:
        first_lock.unlock()

    acquired_after, after_lock = main.try_acquire_single_instance(lock_path)
    assert acquired_after is True
    assert after_lock is not None
    after_lock.unlock()


def test_stale_lock_is_taken_over_after_crash(tmp_path):
    main = _import_main()
    lock_path = str(tmp_path / "single_instance.lock")
    holder_code = (
        "import sys, time; sys.path.insert(0, %r);"
        "from main import try_acquire_single_instance;"
        "ok, _lock = try_acquire_single_instance(%r);"
        "assert ok, 'holder failed to acquire';"
        "time.sleep(60)"
    ) % (REPO_ROOT, lock_path)
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")

    holder = subprocess.Popen(
        [sys.executable, "-c", holder_code],
        env=env,
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 15
        while not os.path.exists(lock_path) and time.time() < deadline:
            time.sleep(0.1)
        assert os.path.exists(lock_path), "holder did not create the lock file"

        # 락 보유 중에는 두 번째 획득이 실패해야 한다.
        acquired, _ = main.try_acquire_single_instance(lock_path)
        assert acquired is False

        # 크래시(강제 종료) 후에는 잔해 락을 회수해야 한다.
        holder.kill()
        holder.wait(timeout=15)
        acquired_after, after_lock = main.try_acquire_single_instance(lock_path)
        assert acquired_after is True
        assert after_lock is not None
        after_lock.unlock()
    finally:
        if holder.poll() is None:
            holder.kill()
            holder.wait(timeout=15)


def test_focus_existing_instance_without_window_returns_false():
    main = _import_main()
    # 실행 중인 인스턴스가 없으면 False (예외 없이).
    assert main.focus_existing_instance("__no_such_pdf_master_window__") is False


def test_startup_splash_missing_asset_returns_none():
    main = _import_main()
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    assert main.show_startup_splash(app, "/nonexistent/splash.png") is None


def test_lock_storage_failure_continues_without_guard(tmp_path):
    main = _import_main()
    acquired, lock = main.try_acquire_single_instance(str(tmp_path / "missing" / "app.lock"))
    assert acquired is True
    assert lock is None


def test_startup_splash_bundled_asset_can_be_shown():
    main = _import_main()
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    splash = main.show_startup_splash(app)
    try:
        assert splash is not None
        assert splash.isVisible()
    finally:
        if splash is not None:
            splash.close()


def test_import_failure_closes_startup_splash():
    code = r'''
import builtins
import main
class Splash:
    closed = False
    def close(self):
        self.closed = True
splash = Splash()
main.show_startup_splash = lambda app: splash
main.try_acquire_single_instance = lambda: (True, None)
original_import = builtins.__import__
def fail_window_import(name, *args, **kwargs):
    if name == "src.ui.main_window":
        raise ImportError("startup regression sentinel")
    return original_import(name, *args, **kwargs)
builtins.__import__ = fail_window_import
try:
    main.main()
except ImportError as error:
    assert str(error) == "startup regression sentinel"
else:
    raise AssertionError("startup import unexpectedly succeeded")
assert splash.closed
'''
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO_ROOT,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
