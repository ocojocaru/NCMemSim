# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

from ncmemsim.ensemble import (
    EnsembleReport,
    EnsembleReportStudy,
    build_ensemble_report,
    write_ensemble_report,
)
from ncmemsim.ensemble.reporting import (
    EnsembleReport as ReportingEnsembleReport,
    EnsembleReportStudy as ReportingEnsembleReportStudy,
    build_ensemble_report as reporting_build_ensemble_report,
    write_ensemble_report as reporting_write_ensemble_report,
)


def test_k6a_reporting_public_api_exports_canonical_objects():
    assert EnsembleReport is ReportingEnsembleReport
    assert EnsembleReportStudy is ReportingEnsembleReportStudy
    assert build_ensemble_report is reporting_build_ensemble_report
    assert write_ensemble_report is reporting_write_ensemble_report
