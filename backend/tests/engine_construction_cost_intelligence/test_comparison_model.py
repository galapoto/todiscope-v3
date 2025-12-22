from __future__ import annotations

import pytest

from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
from backend.app.engines.construction_cost_intelligence.errors import (
    DatasetVersionInvalidError,
    DatasetVersionMismatchError,
    IdentityInvalidError,
)
from backend.app.engines.construction_cost_intelligence.models import (
    ComparisonConfig,
    CostLine,
    NormalizationMapping,
    normalize_cost_lines,
)


def test_cost_line_requires_dataset_version_id() -> None:
    with pytest.raises(DatasetVersionInvalidError):
        CostLine(
            dataset_version_id="",
            kind="boq",
            line_id="L1",
            identity={"item_code": "A"},
        )


def test_cost_line_identity_is_immutable_mapping() -> None:
    line = CostLine(
        dataset_version_id=str(uuid7()),
        kind="boq",
        line_id="L1",
        identity={"item_code": "A"},
        attributes={"x": 1},
    )
    with pytest.raises(TypeError):
        line.identity["item_code"] = "B"  # type: ignore[misc]
    with pytest.raises(TypeError):
        line.attributes["x"] = 2  # type: ignore[misc]


def test_normalize_cost_lines_binds_dataset_version() -> None:
    dv_id = str(uuid7())
    mapping = NormalizationMapping(
        line_id="id",
        identity={"item_code": "code"},
        quantity="qty",
        unit_cost="rate",
        currency="ccy",
        extras=("note",),
    )
    normalized = normalize_cost_lines(
        dataset_version_id=dv_id,
        kind="boq",
        raw_lines=[{"id": "L1", "code": "A", "qty": "2", "rate": "10", "ccy": "EUR", "note": "x"}],
        mapping=mapping,
    )
    assert len(normalized) == 1
    assert normalized[0].dataset_version_id == dv_id
    assert normalized[0].quantity is not None and str(normalized[0].quantity) == "2"
    assert normalized[0].unit_cost is not None and str(normalized[0].unit_cost) == "10"
    assert normalized[0].currency == "EUR"
    assert normalized[0].attributes.get("note") == "x"


def test_compare_enforces_dataset_version_consistency() -> None:
    cfg = ComparisonConfig(identity_fields=("item_code",))
    with pytest.raises(DatasetVersionMismatchError):
        dv1 = str(uuid7())
        dv2 = str(uuid7())
        compare_boq_to_actuals(
            dataset_version_id=dv1,
            boq_lines=[CostLine(dataset_version_id=dv1, kind="boq", line_id="b1", identity={"item_code": "A"})],
            actual_lines=[CostLine(dataset_version_id=dv2, kind="actual", line_id="a1", identity={"item_code": "A"})],
            config=cfg,
        )


def test_compare_aligns_lines_and_computes_delta_without_interpretation() -> None:
    dv_id = str(uuid7())
    cfg = ComparisonConfig(identity_fields=("item_code",), cost_basis="prefer_total_cost")
    boq = [
        CostLine(
            dataset_version_id=dv_id,
            kind="boq",
            line_id="b1",
            identity={"item_code": "A"},
            quantity="2",
            unit_cost="10",
        )
    ]
    actual = [
        CostLine(
            dataset_version_id=dv_id,
            kind="actual",
            line_id="a1",
            identity={"item_code": "A"},
            total_cost="25",
        )
    ]

    res = compare_boq_to_actuals(dataset_version_id=dv_id, boq_lines=boq, actual_lines=actual, config=cfg)
    assert res.dataset_version_id == dv_id
    assert len(res.matched) == 1
    assert res.matched[0].match_key == "item_code=A"
    assert str(res.matched[0].boq_total_cost) == "20"
    assert str(res.matched[0].actual_total_cost) == "25"
    assert str(res.matched[0].cost_delta) == "5"
    assert res.matched[0].boq_incomplete_cost_count == 0
    assert res.matched[0].actual_incomplete_cost_count == 0
    assert res.unmatched_boq == ()
    assert res.unmatched_actual == ()
    assert res.breakdowns == ()


def test_compare_requires_identity_fields_present() -> None:
    cfg = ComparisonConfig(identity_fields=("item_code", "cost_code"))
    boq = [CostLine(dataset_version_id=str(uuid7()), kind="boq", line_id="b1", identity={"item_code": "A"})]
    actual: list[CostLine] = []
    with pytest.raises(IdentityInvalidError):
        compare_boq_to_actuals(dataset_version_id=boq[0].dataset_version_id, boq_lines=boq, actual_lines=actual, config=cfg)


def test_compare_can_break_down_by_category_dimension() -> None:
    dv_id = str(uuid7())
    cfg = ComparisonConfig(identity_fields=("item_code",), breakdown_fields=("category",))
    boq = [
        CostLine(
            dataset_version_id=dv_id,
            kind="boq",
            line_id="b1",
            identity={"item_code": "A"},
            total_cost="10",
            attributes={"category": "labor"},
        ),
        CostLine(
            dataset_version_id=dv_id,
            kind="boq",
            line_id="b2",
            identity={"item_code": "B"},
            total_cost="20",
            attributes={"category": "materials"},
        ),
    ]
    actual = [
        CostLine(
            dataset_version_id=dv_id,
            kind="actual",
            line_id="a1",
            identity={"item_code": "A"},
            total_cost="12",
            attributes={"category": "labor"},
        ),
        CostLine(
            dataset_version_id=dv_id,
            kind="actual",
            line_id="a2",
            identity={"item_code": "B"},
            total_cost="18",
            attributes={"category": "materials"},
        ),
    ]

    res = compare_boq_to_actuals(dataset_version_id=dv_id, boq_lines=boq, actual_lines=actual, config=cfg)
    keys = [b.breakdown_key for b in res.breakdowns]
    assert keys == ["category=labor", "category=materials"]
    labor = res.breakdowns[0]
    assert str(labor.boq_total_cost) == "10"
    assert str(labor.actual_total_cost) == "12"
    assert str(labor.cost_delta) == "2"
    assert labor.boq_lines_count == 1
    assert labor.actual_lines_count == 1
    assert labor.dimensions["category"] == "labor"
