from __future__ import annotations

import argparse
from pathlib import Path

from app.services.extraction_quality import (
    ExtractionQualityService,
)
from app.services.source_discovery import (
    SourceDiscoveryService,
)
from app.services.source_extraction import (
    SourceExtractionService,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a read-only extraction quality report."
    )

    parser.add_argument(
        "--startup",
        required=True,
    )

    parser.add_argument(
        "--data-root",
        default="/opt/investment-os/data/real_startups",
    )

    args = parser.parse_args()

    source_root = (
        Path(args.data_root)
        / args.startup
        / "sources"
    )

    discovery = SourceDiscoveryService()
    extraction = SourceExtractionService()
    quality_service = ExtractionQualityService()

    sources = discovery.discover(
        startup_id=args.startup,
        source_root=source_root,
    )

    reports = []

    for source in sources:
        try:
            content = extraction.extract(
                source=source,
                source_root=source_root,
            )

            processor_name = None

            report = quality_service.assess(
                source=source,
                content=content,
                processor_name=processor_name,
            )

        except Exception as exc:
            from app.models.extraction_quality import (
                ExtractionQuality,
                ExtractionQualityReport,
            )

            report = ExtractionQualityReport(
                source_id=str(source.source_id),
                relative_path=source.relative_path,
                source_type=source.source_type.value,
                source_category=source.source_category.value,
                quality=ExtractionQuality.FAIL,
                text_length=0,
                segment_count=0,
                warnings=[
                    f"extraction_error: {exc}"
                ],
            )

        reports.append(report)

    print("=" * 110)
    print(
        f"{args.startup.upper()} EXTRACTION QUALITY REPORT"
    )
    print("=" * 110)

    print(
        f"{'QUALITY':8s} | "
        f"{'TYPE':5s} | "
        f"{'TEXT':8s} | "
        f"{'SEG':5s} | "
        f"SOURCE"
    )

    print("-" * 110)

    for report in reports:
        print(
            f"{report.quality.value.upper():8s} | "
            f"{report.source_type:5s} | "
            f"{report.text_length:8d} | "
            f"{report.segment_count:5d} | "
            f"{report.relative_path}"
        )

        for warning in report.warnings:
            print(
                f"         WARNING: {warning}"
            )

    print()
    print("=" * 110)
    print("SUMMARY")
    print("=" * 110)

    counts = {
        "pass": 0,
        "review": 0,
        "fail": 0,
    }

    for report in reports:
        counts[report.quality.value] += 1

    print("TOTAL  :", len(reports))
    print("PASS   :", counts["pass"])
    print("REVIEW :", counts["review"])
    print("FAIL   :", counts["fail"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
