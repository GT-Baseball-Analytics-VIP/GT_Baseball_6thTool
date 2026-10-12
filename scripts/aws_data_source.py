"""Read-only access to the shared GTBA TrackMan PostgreSQL database."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd
from gtba_data import query_df


def list_games(
    limit: int = 1000,
    *,
    team_code: str | None = None,
) -> pd.DataFrame:
    """Return recent games with pitch counts, optionally limited to one team."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    conditions = ["TRUE"]
    params: list[Any] = []
    if team_code:
        conditions.append("(home_team = %s OR away_team = %s)")
        params.extend([team_code, team_code])
    params.append(limit)

    return query_df(
        f"""
        SELECT
            game_id AS "GameID",
            MIN(date) AS "GameDate",
            MIN(home_team) AS "HomeTeam",
            MIN(away_team) AS "AwayTeam",
            COUNT(*) AS "PitchCount"
        FROM analytics.trackman_pitches
        WHERE {" AND ".join(conditions)}
        GROUP BY game_id
        ORDER BY MAX(date) DESC NULLS LAST, game_id DESC
        LIMIT %s
        """,
        tuple(params),
    )


def load_pitch_data(
    *,
    game_ids: Sequence[str] | None = None,
    pitcher: str | None = None,
    batter: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Load pitch data enriched with the related AWS analytics views.

    The related views are one row per pitch and must be joined with
    ``pitch_uid``.  Runner tracking and fielder-event metrics are not exposed
    by the current analytics schema and are intentionally not synthesized here.
    """
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1 when provided")

    conditions: list[str] = []
    params: list[Any] = []

    if game_ids:
        conditions.append("p.game_id = ANY(%s)")
        params.append(list(game_ids))
    if pitcher:
        conditions.append("p.pitcher = %s")
        params.append(pitcher)
    if batter:
        conditions.append("p.batter = %s")
        params.append(batter)

    where_clause = " AND ".join(conditions) or "TRUE"
    limit_clause = " LIMIT %s" if limit is not None else ""
    if limit is not None:
        params.append(limit)

    return query_df(
        f"""
        SELECT
            p.pitch_uid AS "PitchUID",
            p.game_id AS "GameID",
            p.date AS "GameDate",
            p.time AS "PitchTime",
            p.pitch_no AS "PitchNumber",
            p.pa_of_inning AS "PlateAppearance",
            p.pa_of_inning AS "AtBat",
            p.pitch_of_pa AS "PitchOfPlateAppearance",
            p.inning AS "Inning",
            p.top_bottom AS "TopBottom",
            p.outs AS "Outs",
            p.balls AS "Balls",
            p.strikes AS "Strikes",
            p.pitcher AS "PitcherName",
            p.pitcher_id AS "PitcherID",
            p.pitcher_throws AS "PitcherThrows",
            p.pitcher_team AS "PitcherTeam",
            p.batter AS "BatterName",
            p.batter_id AS "BatterID",
            p.batter_side AS "BatterSide",
            p.batter_team AS "BatterTeam",
            p.tagged_pitch_type AS "TaggedPitchType",
            p.auto_pitch_type AS "AutoPitchType",
            p.pitch_call AS "PitchCall",
            p.kor_bb AS "StrikeoutOrWalk",
            p.tagged_hit_type AS "TaggedHitType",
            p.play_result AS "PlayResult",
            p.rel_speed AS "PitchVelo",
            p.spin_rate AS "SpinRate",
            p.spin_axis AS "SpinAxis",
            p.plate_loc_height AS "PlateLocHeight",
            p.plate_loc_side AS "PlateLocSide",
            p.exit_speed AS "ExitVelo",
            p.angle AS "LaunchAng",
            p.direction AS "HitDirection",
            p.home_team AS "HomeTeam",
            p.away_team AS "AwayTeam",
            p.stadium AS "Stadium",
            p.level AS "Level",
            p.league AS "League",
            (p.pitch_call = 'InPlay') AS "BallInPlay",

            -- Batted-ball analytics
            bb.play_id AS "BattedBallPlayID",
            bb.hit_spin_rate AS "HitSpinRate",
            bb.distance AS "ActualDistance",
            bb.bearing AS "HitBearing",
            bb.hang_time AS "HangTime",
            bb.max_height AS "MaxHeight",
            bb.auto_hit_type AS "AutoHitType",
            bb.position_at_110_x AS "PositionAt110X",
            bb.position_at_110_y AS "PositionAt110Y",
            bb.position_at_110_z AS "PositionAt110Z",
            bb.last_tracked_distance AS "LastTrackedDistance",

            -- Pitch movement analytics
            pm.effective_velo AS "EffectiveVelo",
            pm.zone_speed AS "ZoneSpeed",
            pm.tilt AS "PitchTilt",
            pm.rel_height AS "ReleaseHeight",
            pm.rel_side AS "ReleaseSide",
            pm.extension AS "Extension",
            pm.vert_break AS "VerticalBreak",
            pm.induced_vert_break AS "InducedVerticalBreak",
            pm.horz_break AS "HorizontalBreak",
            pm.vert_appr_angle AS "VerticalApproachAngle",
            pm.horz_appr_angle AS "HorizontalApproachAngle",
            pm.zone_time AS "ZoneTime",
            pm.pfxx AS "PFXx",
            pm.pfxz AS "PFXz",

            -- Defensive positioning at pitch release
            pos.detected_shift AS "DetectedShift",
            pos.first_base_position_at_release_x AS "FirstBasePositionX",
            pos.first_base_position_at_release_z AS "FirstBasePositionZ",
            pos.second_base_position_at_release_x AS "SecondBasePositionX",
            pos.second_base_position_at_release_z AS "SecondBasePositionZ",
            pos.third_base_position_at_release_x AS "ThirdBasePositionX",
            pos.third_base_position_at_release_z AS "ThirdBasePositionZ",
            pos.shortstop_position_at_release_x AS "ShortstopPositionX",
            pos.shortstop_position_at_release_z AS "ShortstopPositionZ",
            pos.left_field_position_at_release_x AS "LeftFieldPositionX",
            pos.left_field_position_at_release_z AS "LeftFieldPositionZ",
            pos.center_field_position_at_release_x AS "CenterFieldPositionX",
            pos.center_field_position_at_release_z AS "CenterFieldPositionZ",
            pos.right_field_position_at_release_x AS "RightFieldPositionX",
            pos.right_field_position_at_release_z AS "RightFieldPositionZ"
        FROM analytics.trackman_pitches AS p
        LEFT JOIN analytics.trackman_batted_ball AS bb
            ON bb.pitch_uid = p.pitch_uid
        LEFT JOIN analytics.trackman_pitch_movement AS pm
            ON pm.pitch_uid = p.pitch_uid
        LEFT JOIN analytics.player_positioning AS pos
            ON pos.pitch_uid = p.pitch_uid
        WHERE {where_clause}
        ORDER BY p.date NULLS LAST, p.game_id, p.pitch_no
        {limit_clause}
        """,
        tuple(params),
    )


def get_view_columns(view_name: str) -> pd.DataFrame:
    """Return column metadata for a view in the analytics schema."""
    if not view_name.replace("_", "").isalnum():
        raise ValueError("view_name must contain only letters, numbers, and underscores")

    return query_df(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'analytics'
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (view_name,),
    )
