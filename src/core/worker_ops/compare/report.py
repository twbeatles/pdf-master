"""비교 리포트(마크다운) 생성 + 결과 payload/완료 시그널."""
from __future__ import annotations

import os
from typing import Any

from ..._typing import WorkerHost


class WorkerCompareReportMixin(WorkerHost):
    def _build_compare_report_lines(
        self,
        *,
        file_path1: str,
        file_path2: str,
        results: list[dict[str, Any]],
        visual_diff_path: str | None,
    ) -> list[str]:
        report_lines = [
            f"# {self._get_msg('compare_report_title')}",
            "",
            f"{self._get_msg('compare_report_file1')}: {os.path.basename(file_path1)}",
            f"{self._get_msg('compare_report_file2')}: {os.path.basename(file_path2)}",
            "",
        ]
        if results:
            for result in results:
                page_number = result["page"]
                status = result["status"]
                report_lines.append(f"## {self._get_msg('compare_report_page', page_number)}")
                if status == "missing_file1":
                    report_lines.append(f"- {self._get_msg('compare_report_missing_file1')}")
                elif status == "missing_file2":
                    report_lines.append(f"- {self._get_msg('compare_report_missing_file2')}")
                elif status == "visual_error":
                    report_lines.append(f"- {self._get_msg('compare_report_visual_error')}")
                    for sample in result.get("samples", []):
                        report_lines.append(f"- {self._get_msg('compare_report_sample', sample)}")
                elif status == "visual_diff":
                    report_lines.append(f"- {self._get_msg('compare_report_visual_diff')}")
                    for sample in result.get("samples", []):
                        report_lines.append(f"- {self._get_msg('compare_report_sample', sample)}")
                else:
                    report_lines.append(
                        f"- {self._get_msg('compare_report_added', result.get('added', 0))}"
                    )
                    report_lines.append(
                        f"- {self._get_msg('compare_report_deleted', result.get('deleted', 0))}"
                    )
                    report_lines.append(
                        f"- {self._get_msg('compare_report_modified', result.get('modified', 0))}"
                    )
                    for sample in result.get("samples", []):
                        report_lines.append(f"- {self._get_msg('compare_report_sample', sample)}")
                report_lines.append("")
        else:
            report_lines.append(self._get_msg("compare_report_identical"))
        if visual_diff_path:
            report_lines.extend(
                [
                    "",
                    f"- {self._get_msg('compare_report_visual_path', os.path.basename(visual_diff_path))}",
                ]
            )
        report_lines.append("")
        return report_lines

    def _finish_compare(
        self,
        *,
        results: list[dict[str, Any]],
        output_path: str,
        visual_diff_path: str | None,
    ) -> None:
        visual_error_count = sum(1 for result in results if result.get("status") == "visual_error")
        diff_count = sum(1 for result in results if result.get("status") not in {"same", "visual_error"})
        self._set_result_payload(
            diff_count=diff_count,
            visual_error_count=visual_error_count,
            results=results,
            report_path=output_path,
            visual_diff_path=visual_diff_path or "",
        )
        self.finished_signal.emit(
            self._get_msg(
                "msg_compare_pdfs_done",
                diff_count,
                self._get_msg("msg_compare_pdfs_visual_diff_suffix") if visual_diff_path else "",
            )
        )


__all__ = ["WorkerCompareReportMixin"]
