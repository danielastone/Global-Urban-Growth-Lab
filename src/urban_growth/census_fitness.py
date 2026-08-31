"""Analysis-specific fitness evidence for validated census cohorts."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.data_fitness import evaluate_city_data_fitness, headline_sample
from urban_growth.io import require_columns

US_CENSUS_FITNESS_SCOPE = "us_census_place_2010_2020_threshold_pilot"


def apply_us_census_place_fitness(cohort: pd.DataFrame) -> pd.DataFrame:
    """Attach City Data Fitness evidence to the validated U.S. place cohort.

    The upstream cohort has already enforced one-to-one place relationships and
    >=99.5% land overlap. This function translates that evidence into the common
    fitness vocabulary without modifying the original cohort fields.

    The cohort is suitable for level/growth headline work inside the registered
    25k-100k origin-population design. It is not spatial/network eligible because
    the pilot does not validate coordinates or network geography.
    """
    require_columns(
        cohort,
        {
            "settlement_id",
            "geography_status",
            "origin_land_overlap",
            "endpoint_land_overlap",
            "origin_population_status",
            "endpoint_population_status",
        },
        source_name="U.S. Census threshold cohort",
    )
    out = cohort.copy()
    accepted = out["geography_status"].isin({"stable", "official_crosswalk"})
    direct_counts = out["origin_population_status"].eq("direct_decennial_enumeration") & out[
        "endpoint_population_status"
    ].eq("direct_decennial_enumeration")
    overlap_valid = out["origin_land_overlap"].ge(0.995) & out["endpoint_land_overlap"].ge(0.995)

    out["fitness_scope"] = US_CENSUS_FITNESS_SCOPE
    out["source_id"] = "us_census_decennial_place_2010_2020"
    out["population_concept"] = "census_place_total_population"
    out["geographic_unit"] = "census_place"
    out["reference_date"] = "2010-04-01/2020-04-01"
    out["observation_type"] = "direct_decennial_enumeration"
    out["temporal_comparable"] = direct_counts
    out["geographic_comparable"] = accepted & overlap_valid
    out["boundary_temporally_fixed"] = out["geography_status"].eq("stable")
    out["boundary_change_status"] = np.where(
        out["geography_status"].eq("stable"), "none", "official_crosswalk"
    )
    out["administrative_reclassification"] = False
    out["methodology_change"] = False
    out["minimum_reporting_threshold"] = 0
    out["truncation_exposure"] = "low"
    out["survivorship_exposure"] = "low"
    out["concordance_method"] = "census_place_relationship_one_to_one_land_overlap_0.995"
    out["concordance_status"] = out["geography_status"]
    out["known_inconsistency"] = False
    out["validation_status"] = np.where(accepted & direct_counts & overlap_valid, "passed", "failed")
    out["coordinates_validated"] = False
    out["network_geography_validated"] = False
    out["fitness_note"] = (
        "Eligibility applies only to the registered 25k-100k 2010 origin cohort; "
        "spatial/network use requires separate geometry validation."
    )
    return evaluate_city_data_fitness(out)


def us_census_headline_sample(cohort: pd.DataFrame) -> pd.DataFrame:
    """Return the registered U.S. threshold cohort after the common headline gate."""
    return headline_sample(apply_us_census_place_fitness(cohort))
