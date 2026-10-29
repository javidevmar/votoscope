"""Gold layer: read-only views for the web frontend.

Single source for the view SQL: the alembic migration executes these
statements and the tests create the same views in throwaway schemas, so the
SQL under test is the deployed one. Aggregates and percentages live only
here: ``silver`` keeps the facts (see .agents/data-model.md).
"""

from __future__ import annotations

# Creation order: results first, polls afterwards. There are no dependencies
# between views. Schema placeholders are filled by ``view_ddl``.
_VIEW_SQL: dict[str, str] = {
    "election_summary": """CREATE VIEW {gold}.election_summary AS
SELECT e.id AS election_id,
       e.type AS election_type,
       e.date AS election_date,
       e.name AS election_name,
       t.census, t.null_votes, t.blank_votes,
       coalesce(vt.candidature_votes, 0) AS candidature_votes,
       coalesce(vt.candidature_votes, 0) + t.blank_votes AS valid_votes,
       coalesce(vt.candidature_votes, 0) + t.blank_votes + t.null_votes AS voters,
       round((coalesce(vt.candidature_votes, 0) + t.blank_votes + t.null_votes) * 100.0
             / nullif(t.census, 0), 2) AS turnout_pct
FROM {silver}.election e
JOIN (
    SELECT election_id, sum(census) AS census, sum(null_votes) AS null_votes,
           sum(blank_votes) AS blank_votes
    FROM {silver}.turnout GROUP BY election_id
) t ON t.election_id = e.id
LEFT JOIN (
    SELECT pe.election_id, sum(v.votes) AS candidature_votes
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    GROUP BY pe.election_id
) vt ON vt.election_id = e.id""",
    "result_by_area": """CREATE VIEW {gold}.result_by_area AS
WITH area_votes AS (
    SELECT pe.election_id, 'national'::text AS level,
           NULL::text AS community_ine_code, NULL::text AS community_name,
           NULL::text AS province_ine_code, NULL::text AS province_name,
           NULL::integer AS municipality_id, NULL::text AS municipality_ine_code,
           NULL::text AS municipality_name,
           pe.party_id, sum(v.votes) AS votes
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    UNION ALL
    SELECT pe.election_id, 'community',
           p.autonomous_community_ine_code, c.name, NULL::text, NULL::text,
           NULL::integer, NULL::text, NULL::text,
           pe.party_id, sum(v.votes)
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    JOIN {silver}.polling_station s ON s.id = v.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
    GROUP BY 1, 3, 4, 10
    UNION ALL
    SELECT pe.election_id, 'province',
           p.autonomous_community_ine_code, c.name, p.ine_code, p.name,
           NULL::integer, NULL::text, NULL::text,
           pe.party_id, sum(v.votes)
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    JOIN {silver}.polling_station s ON s.id = v.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
    GROUP BY 1, 3, 4, 5, 6, 10
    UNION ALL
    SELECT pe.election_id, 'municipality',
           p.autonomous_community_ine_code, c.name, p.ine_code, p.name,
           m.id, m.ine_code, m.name,
           pe.party_id, sum(v.votes)
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    JOIN {silver}.polling_station s ON s.id = v.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
    GROUP BY 1, 3, 4, 5, 6, 7, 8, 9, 10
),
area_blank AS (
    SELECT t.election_id, 'national'::text AS level,
           NULL::text AS community_ine_code, NULL::text AS province_ine_code,
           NULL::integer AS municipality_id,
           sum(t.blank_votes) AS blank_votes
    FROM {silver}.turnout t
    GROUP BY 1, 2, 3, 4, 5
    UNION ALL
    SELECT t.election_id, 'community', p.autonomous_community_ine_code, NULL::text,
           NULL::integer, sum(t.blank_votes)
    FROM {silver}.turnout t
    JOIN {silver}.polling_station s ON s.id = t.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    GROUP BY 1, 2, 3, 4, 5
    UNION ALL
    SELECT t.election_id, 'province', p.autonomous_community_ine_code, p.ine_code,
           NULL::integer, sum(t.blank_votes)
    FROM {silver}.turnout t
    JOIN {silver}.polling_station s ON s.id = t.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    GROUP BY 1, 2, 3, 4, 5
    UNION ALL
    SELECT t.election_id, 'municipality', p.autonomous_community_ine_code, p.ine_code,
           m.id, sum(t.blank_votes)
    FROM {silver}.turnout t
    JOIN {silver}.polling_station s ON s.id = t.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    GROUP BY 1, 2, 3, 4, 5
),
area_totals AS (
    SELECT av.*,
           sum(av.votes) OVER (
               PARTITION BY av.election_id, av.level, av.community_ine_code,
                            av.province_ine_code, av.municipality_id
           ) AS candidature_votes
    FROM area_votes av
)
SELECT at.election_id, at.level,
       at.community_ine_code, at.community_name,
       at.province_ine_code, at.province_name,
       at.municipality_id, at.municipality_ine_code, at.municipality_name,
       p.id AS party_id, p.slug AS party_slug, p.name AS party_name,
       p.color AS party_color,
       at.votes,
       round(at.votes * 100.0 / nullif(at.candidature_votes + ab.blank_votes, 0), 2) AS pct
FROM area_totals at
JOIN area_blank ab
  ON ab.election_id = at.election_id
 AND ab.level = at.level
 AND ab.community_ine_code IS NOT DISTINCT FROM at.community_ine_code
 AND ab.province_ine_code IS NOT DISTINCT FROM at.province_ine_code
 AND ab.municipality_id IS NOT DISTINCT FROM at.municipality_id
JOIN {silver}.party p ON p.id = at.party_id""",
    "result_by_station": """CREATE VIEW {gold}.result_by_station AS
WITH station_party AS (
    SELECT v.polling_station_id, pe.election_id, pe.party_id, sum(v.votes) AS votes
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    GROUP BY 1, 2, 3
),
station_valid AS (
    SELECT polling_station_id, election_id, sum(votes) AS candidature_votes
    FROM station_party
    GROUP BY 1, 2
)
SELECT sp.election_id, sp.polling_station_id,
       s.district, s.section, s.code,
       m.id AS municipality_id, m.ine_code AS municipality_ine_code,
       m.name AS municipality_name,
       p.ine_code AS province_ine_code, p.name AS province_name,
       c.ine_code AS community_ine_code, c.name AS community_name,
       pa.id AS party_id, pa.slug AS party_slug, pa.name AS party_name,
       pa.color AS party_color,
       sp.votes,
       round(sp.votes * 100.0 / nullif(sv.candidature_votes + t.blank_votes, 0), 2) AS pct
FROM station_party sp
JOIN station_valid sv ON sv.polling_station_id = sp.polling_station_id
                     AND sv.election_id = sp.election_id
JOIN {silver}.polling_station s ON s.id = sp.polling_station_id
JOIN {silver}.municipality m ON m.id = s.municipality_id
JOIN {silver}.province p ON p.ine_code = m.province_ine_code
JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
JOIN {silver}.turnout t ON t.polling_station_id = sp.polling_station_id
                       AND t.election_id = sp.election_id
JOIN {silver}.party pa ON pa.id = sp.party_id""",
    "station_turnout": """CREATE VIEW {gold}.station_turnout AS
WITH station_valid AS (
    SELECT v.polling_station_id, pe.election_id, sum(v.votes) AS candidature_votes
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    GROUP BY 1, 2
)
SELECT t.election_id, t.polling_station_id,
       s.district, s.section, s.code,
       m.id AS municipality_id, m.ine_code AS municipality_ine_code,
       m.name AS municipality_name,
       p.ine_code AS province_ine_code, p.name AS province_name,
       c.ine_code AS community_ine_code, c.name AS community_name,
       t.census, t.null_votes, t.blank_votes,
       coalesce(sv.candidature_votes, 0) AS candidature_votes,
       coalesce(sv.candidature_votes, 0) + t.blank_votes AS valid_votes,
       coalesce(sv.candidature_votes, 0) + t.blank_votes + t.null_votes AS voters,
       round((coalesce(sv.candidature_votes, 0) + t.blank_votes + t.null_votes) * 100.0
             / nullif(t.census, 0), 2) AS turnout_pct
FROM {silver}.turnout t
JOIN {silver}.polling_station s ON s.id = t.polling_station_id
JOIN {silver}.municipality m ON m.id = s.municipality_id
JOIN {silver}.province p ON p.ine_code = m.province_ine_code
JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
LEFT JOIN station_valid sv ON sv.polling_station_id = t.polling_station_id
                          AND sv.election_id = t.election_id""",
    "poll_flat": """CREATE VIEW {gold}.poll_flat AS
SELECT p.id AS poll_id,
       ps.id AS pollster_id, ps.slug AS pollster_slug, ps.name AS pollster_name,
       p.source, p.election_type, p.election_id,
       p.fieldwork_start, p.fieldwork_end, p.sample_size, p.turnout, p.revision_id,
       pt.id AS party_id, pt.slug AS party_slug, pt.name AS party_name,
       pt.color AS party_color,
       r.pct, r.seats_min, r.seats_max
FROM {silver}.poll_result r
JOIN {silver}.poll p ON p.id = r.poll_id
JOIN {silver}.pollster ps ON ps.id = p.pollster_id
JOIN {silver}.party pt ON pt.id = r.party_id""",
    "poll_trend": """CREATE VIEW {gold}.poll_trend AS
SELECT p.id AS poll_id,
       coalesce(p.fieldwork_end, p.fieldwork_start) AS poll_date,
       ps.slug AS pollster_slug, ps.name AS pollster_name,
       p.source, p.revision_id, p.election_type, p.election_id,
       pt.id AS party_id, pt.slug AS party_slug, pt.name AS party_name,
       pt.color AS party_color,
       r.pct, r.seats_min, r.seats_max
FROM {silver}.poll_result r
JOIN {silver}.poll p ON p.id = r.poll_id
JOIN {silver}.pollster ps ON ps.id = p.pollster_id
JOIN {silver}.party pt ON pt.id = r.party_id
ORDER BY poll_date, p.id, pt.slug""",
}


def view_ddl(
    gold_schema: str = "gold", silver_schema: str = "silver"
) -> dict[str, str]:
    """Return the ``CREATE VIEW`` statements by view name, schema-parametrised."""
    return {
        name: sql.format(gold=gold_schema, silver=silver_schema)
        for name, sql in _VIEW_SQL.items()
    }
