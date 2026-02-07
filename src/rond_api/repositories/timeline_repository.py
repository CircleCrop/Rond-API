"""Timeline 数据仓储。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from rond_api.db.sqlite_client import SQLiteReadClient


class TimelineRepository:
    """封装时间线查询 SQL。"""

    def __init__(self, client: SQLiteReadClient) -> None:
        self._client = client

    def fetch_visits(self, day_start_core: float, day_end_core: float) -> list[dict[str, Any]]:
        """查询与目标自然日有重叠的到访。"""

        sql = """
        SELECT
            v.Z_PK AS visit_id,
            v.ZLOCATION AS location_id,
            v.ZARRIVALDATE_ AS arrival_core,
            v.ZDEPARTUREDATE_ AS departure_core,
            rv.ZNAME AS raw_name,
            rv.ZTHOROUGHFARE AS raw_thoroughfare,
            rv.ZLATITUDE AS raw_latitude,
            rv.ZLONGITUDE AS raw_longitude,
            l.ZTYPE_ AS location_type,
            l.ZCATEGORY_ AS poi_category,
            COALESCE(NULLIF(l.ZNAME_, ''), '未知地点') AS location_name,
            COALESCE(NULLIF(la.ZNAME_, ''), NULLIF(va.ZNAME_, ''), '未分类') AS category_name
        FROM ZVISIT v
        LEFT JOIN ZLOCATION l ON l.Z_PK = v.ZLOCATION
        LEFT JOIN ZACTIVITY la ON la.Z_PK = l.ZUSERACTIVITY_
        LEFT JOIN ZACTIVITY va ON va.Z_PK = v.ZACTIVITY_
        LEFT JOIN ZRAWVISIT rv ON rv.Z_PK = v.ZRAW
        WHERE
            v.ZPARENT IS NULL
            AND v.ZMERGEDTO IS NULL
            AND v.ZARRIVALDATE_ IS NOT NULL
            AND v.ZDEPARTUREDATE_ IS NOT NULL
            AND v.ZARRIVALDATE_ < :day_end_core
            AND v.ZDEPARTUREDATE_ > :day_start_core
        ORDER BY v.ZARRIVALDATE_ ASC, v.Z_PK ASC;
        """
        rows = self._client.execute_query(
            sql,
            {
                "day_start_core": day_start_core,
                "day_end_core": day_end_core,
            },
        )
        return [dict(row) for row in rows]

    def fetch_latest_open_raw_visit(self, day_end_core: float) -> dict[str, Any] | None:
        """查询最新的未结束原始到访。"""

        sql = """
        SELECT
            rv.Z_PK AS raw_id,
            rv.ZARRIVALDATE_ AS arrival_core,
            rv.ZNAME AS raw_name,
            rv.ZTHOROUGHFARE AS raw_thoroughfare,
            rv.ZLATITUDE AS raw_latitude,
            rv.ZLONGITUDE AS raw_longitude
        FROM ZRAWVISIT rv
        WHERE
            rv.ZARRIVALDATE_ IS NOT NULL
            AND rv.ZARRIVALDATE_ < :day_end_core
            AND rv.ZDEPARTUREDATE_ > 60000000000
        ORDER BY rv.ZARRIVALDATE_ DESC
        LIMIT 1;
        """
        rows = self._client.execute_query(sql, {"day_end_core": day_end_core})
        if not rows:
            return None
        return dict(rows[0])

    def fetch_nearby_locations(
        self,
        latitude: float,
        longitude: float,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """按经纬度获取附近地点。"""

        sql = """
        SELECT
            l.Z_PK AS location_id,
            l.ZNAME_ AS location_name,
            l.ZTYPE_ AS location_type,
            l.ZCATEGORY_ AS poi_category,
            l.ZLATITUDE AS latitude,
            l.ZLONGITUDE AS longitude,
            SUM(CASE WHEN va.ZISHOME = 1 THEN 1 ELSE 0 END) AS home_visit_count,
            COUNT(v.Z_PK) AS visit_count
        FROM ZLOCATION l
        LEFT JOIN ZVISIT v
            ON v.ZLOCATION = l.Z_PK
            AND v.ZPARENT IS NULL
            AND v.ZMERGEDTO IS NULL
        LEFT JOIN ZACTIVITY va ON va.Z_PK = v.ZACTIVITY_
        WHERE
            l.ZNAME_ IS NOT NULL
            AND TRIM(l.ZNAME_) <> ''
            AND l.ZLATITUDE IS NOT NULL
            AND l.ZLONGITUDE IS NOT NULL
        GROUP BY l.Z_PK
        ORDER BY
            ((l.ZLATITUDE - :lat) * (l.ZLATITUDE - :lat))
            + ((l.ZLONGITUDE - :lon) * (l.ZLONGITUDE - :lon))
        ASC
        LIMIT :limit;
        """
        rows = self._client.execute_query(
            sql,
            {"lat": latitude, "lon": longitude, "limit": limit},
        )
        return [dict(row) for row in rows]

    def fetch_movements(
        self,
        day_start_core: float,
        day_end_core: float,
    ) -> list[dict[str, Any]]:
        """查询与目标自然日有重叠的交通记录。"""

        sql = """
        SELECT
            m.Z_PK AS movement_id,
            m.ZSTART_ AS start_core,
            m.ZEND_ AS end_core,
            m.ZTYPE_ AS movement_type,
            m.ZTRANSPORT_ AS transport_id,
            t.ZNAME_ AS transport_name,
            m.ZVISITFROM_ AS from_visit_id,
            m.ZVISITTO_ AS to_visit_id,
            lf.ZNAME_ AS from_location_name,
            lt.ZNAME_ AS to_location_name
        FROM ZMOVEMENT m
        LEFT JOIN ZTRANSPORT t ON t.Z_PK = m.ZTRANSPORT_
        LEFT JOIN ZVISIT vf ON vf.Z_PK = m.ZVISITFROM_
        LEFT JOIN ZVISIT vt ON vt.Z_PK = m.ZVISITTO_
        LEFT JOIN ZLOCATION lf ON lf.Z_PK = vf.ZLOCATION
        LEFT JOIN ZLOCATION lt ON lt.Z_PK = vt.ZLOCATION
        WHERE
            m.ZSTART_ IS NOT NULL
            AND m.ZEND_ IS NOT NULL
            AND m.ZSTART_ < :day_end_core
            AND m.ZEND_ > :day_start_core
        ORDER BY m.ZSTART_ ASC, m.Z_PK ASC;
        """
        rows = self._client.execute_query(
            sql,
            {
                "day_start_core": day_start_core,
                "day_end_core": day_end_core,
            },
        )
        return [dict(row) for row in rows]

    def fetch_visit_tags(self, visit_ids: list[int]) -> dict[int, set[str]]:
        """查询 visit 级标签。"""

        if not visit_ids:
            return {}

        placeholders = ",".join("?" for _ in visit_ids)
        sql = f"""
        SELECT
            jv.Z_17VISITS_ AS visit_id,
            t.ZNAME_ AS tag_name
        FROM Z_10VISITS_ jv
        JOIN ZTAG t ON t.Z_PK = jv.Z_10TAGS_5
        WHERE
            jv.Z_17VISITS_ IN ({placeholders})
            AND t.ZNAME_ IS NOT NULL
            AND TRIM(t.ZNAME_) <> '';
        """
        rows = self._client.execute_query(sql, tuple(visit_ids))
        return _rows_to_tag_map(rows, key_name="visit_id")

    def fetch_location_tags(self, location_ids: list[int]) -> dict[int, set[str]]:
        """查询 location 级标签。"""

        if not location_ids:
            return {}

        placeholders = ",".join("?" for _ in location_ids)
        sql = f"""
        SELECT
            jl.Z_5LOCATIONS_ AS location_id,
            t.ZNAME_ AS tag_name
        FROM Z_5TAGS_ jl
        JOIN ZTAG t ON t.Z_PK = jl.Z_10TAGS_2
        WHERE
            jl.Z_5LOCATIONS_ IN ({placeholders})
            AND t.ZNAME_ IS NOT NULL
            AND TRIM(t.ZNAME_) <> '';
        """
        rows = self._client.execute_query(sql, tuple(location_ids))
        return _rows_to_tag_map(rows, key_name="location_id")


def _rows_to_tag_map(rows: list[Any], key_name: str) -> dict[int, set[str]]:
    """将标签行转为映射。"""

    tag_map: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        row_dict = dict(row)
        key_value = row_dict.get(key_name)
        tag_name = row_dict.get("tag_name")
        if key_value is None or tag_name is None:
            continue
        tag_map[int(key_value)].add(str(tag_name))
    return dict(tag_map)
