import json

import pandas as pd
import pytest

from geo_etl.catalog import MRDS
from geo_etl.districts import load_districts
from geo_etl.layers import Options, geology
from geo_etl.rows import COLUMNS

GML = b"""<?xml version="1.0" encoding="UTF-8"?>
<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs" xmlns:gml="http://www.opengis.net/gml"
    xmlns:ms="http://mapserver.gis.umn.edu/mapserver">
  <gml:featureMember>
    <ms:mrds>
      <ms:geometry><gml:Point><gml:coordinates> 75.540000,11.730000 </gml:coordinates></gml:Point></ms:geometry>
      <ms:dep_id> 10087 </ms:dep_id>
      <ms:site_name>Mahe Laterite Pit</ms:site_name>
      <ms:dev_stat>Occurrence</ms:dev_stat>
      <ms:code_list>al fe</ms:code_list>
      <ms:url>https://mrdata.usgs.gov/mrds/show-mrds.php?dep_id=10087</ms:url>
    </ms:mrds>
  </gml:featureMember>
  <gml:featureMember>
    <ms:mrds>
      <ms:geometry><gml:Point><gml:coordinates>75.545,11.725,0</gml:coordinates></gml:Point></ms:geometry>
      <ms:dep_id>10001</ms:dep_id>
      <ms:site_name>Mahe Clay</ms:site_name>
      <ms:code_list>CLY</ms:code_list>
    </ms:mrds>
  </gml:featureMember>
  <gml:featureMember>
    <ms:mrds>
      <ms:geometry><gml:Point><gml:coordinates>80.0,13.0</gml:coordinates></gml:Point></ms:geometry>
      <ms:dep_id>20000</ms:dep_id>
      <ms:code_list>AU</ms:code_list>
    </ms:mrds>
  </gml:featureMember>
  <gml:featureMember>
    <ms:mrds>
      <ms:dep_id>30000</ms:dep_id>
    </ms:mrds>
  </gml:featureMember>
  <gml:featureMember>
    <ms:other><ms:dep_id>40000</ms:dep_id></ms:other>
  </gml:featureMember>
</wfs:FeatureCollection>
"""


def test_parse_mrds_reads_points_and_skips_incomplete():
    points = geology.parse_mrds(GML)
    assert [p["depId"] for p in points] == ["10087", "10001", "20000"]
    first = points[0]
    assert (first["lon"], first["lat"]) == (75.54, 11.73)
    assert first["name"] == "Mahe Laterite Pit"
    assert first["devStat"] == "Occurrence"
    assert first["commodities"] == ["AL", "FE"]
    assert first["url"].endswith("dep_id=10087")
    assert points[1]["url"] == ""
    assert points[1]["devStat"] == ""
    assert (points[1]["lon"], points[1]["lat"]) == (75.545, 11.725)


def test_parse_mrds_empty_collection():
    payload = b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs"/>'
    assert geology.parse_mrds(payload) == []


def test_parse_mrds_rejects_entity_expansion():
    payload = (
        b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]>'
        b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs">&a;</wfs:FeatureCollection>'
    )
    with pytest.raises(Exception, match="(?i)entit"):
        geology.parse_mrds(payload)


def test_assign_points_inside_mahe():
    mahe = load_districts({599})
    inside = geology.assign_points(mahe, geology.parse_mrds(GML))
    assert sorted(p["depId"] for p in inside[599]) == ["10001", "10087"]
    assert geology.assign_points(mahe, []) == {}


def test_run_mrds_counts_without_network(monkeypatch, tmp_path):
    seen = []

    def fake_fetch(bounds):
        seen.append(bounds)
        return geology.parse_mrds(GML)

    monkeypatch.setattr(geology, "fetch_mrds", fake_fetch)
    result = geology.run_mrds(load_districts({599}), Options(cache=tmp_path))
    assert result.failures == []
    assert len(seen) == 1
    xmin, ymin, xmax, ymax = seen[0]
    assert xmin < 75.529 and ymin < 11.702 and xmax > 75.555 and ymax > 11.763
    assert list(result.values.columns) == COLUMNS
    counts = dict(zip(result.values["variable"], result.values["value"], strict=True))
    assert counts == {
        "mineral_occurrences": 2.0,
        "mineral_occurrences_al": 1.0,
        "mineral_occurrences_cly": 1.0,
        "mineral_occurrences_fe": 1.0,
    }
    assert set(result.values["datasetCode"]) == {MRDS.code}
    assert len(result.geology) == 1
    row = result.geology.iloc[0]
    assert row["lithology"] == geology.MRDS_LITHOLOGY
    found = json.loads(row["mineralOccurrences"])
    assert [p["depId"] for p in found] == ["10001", "10087"]


def test_run_mrds_records_failure(monkeypatch, tmp_path):
    def broken(bounds):
        raise RuntimeError("offline")

    monkeypatch.setattr(geology, "fetch_mrds", broken)
    result = geology.run_mrds(load_districts({599}), Options(cache=tmp_path))
    assert result.values.empty
    assert isinstance(result.geology, pd.DataFrame)
    assert result.geology.empty
    assert result.failures == [{"step": "mrds", "districtLgds": [599], "error": "RuntimeError: offline"}]


def test_fetch_mrds_page_limit(monkeypatch):
    class Response:
        content = GML

        def raise_for_status(self):
            return None

    calls = []

    def fake_get(url, params, timeout, headers):
        calls.append(params)
        return Response()

    monkeypatch.setattr(geology.requests, "get", fake_get)
    monkeypatch.setattr(geology, "MRDS_PAGE", 3)
    with pytest.raises(RuntimeError, match="page limit"):
        geology.fetch_mrds((75.0, 11.0, 76.0, 12.0))
    assert calls[0]["bbox"] == "75.00000,11.00000,76.00000,12.00000"
    assert calls[0]["typeName"] == "mrds"
    monkeypatch.setattr(geology, "MRDS_PAGE", 4)
    assert len(geology.fetch_mrds((75.0, 11.0, 76.0, 12.0))) == 3
