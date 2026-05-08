import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from functions.data_processing import convert_rolled_costs_to_direct_costs


def test_total_costs_derived_from_direct_components_when_rolled_total_is_lower_than_children():
    df = pd.DataFrame(
        {
            "index": ["1", "1.1", "1.2"],
            "labor_costs": [50.0, 20.0, 10.0],
            "burden_costs": [20.0, 5.0, 5.0],
            "material_costs": [20.0, 15.0, 10.0],
            "outside_costs": [20.0, 5.0, 10.0],
            # Parent rolled total is lower than the sum of child rolled totals.
            "total_costs": [100.0, 70.0, 60.0],
        }
    )

    result = convert_rolled_costs_to_direct_costs(df)

    assert result.loc[0, "rolled_labor_costs"] == 50.0
    assert result.loc[0, "rolled_burden_costs"] == 20.0
    assert result.loc[0, "rolled_material_costs"] == 20.0
    assert result.loc[0, "rolled_outside_costs"] == 20.0
    assert result.loc[0, "rolled_total_costs"] == 100.0

    direct_component_columns = [
        "labor_costs",
        "burden_costs",
        "material_costs",
        "outside_costs",
    ]
    parent_direct_components = result.loc[0, direct_component_columns]

    assert parent_direct_components.to_dict() == {
        "labor_costs": 20.0,
        "burden_costs": 10.0,
        "material_costs": 0.0,
        "outside_costs": 5.0,
    }
    assert (parent_direct_components >= 0).all()
    assert result.loc[0, "total_costs"] >= 0
    assert result.loc[0, "total_costs"] == parent_direct_components.sum()
    assert result.loc[0, "total_costs"] == 35.0
