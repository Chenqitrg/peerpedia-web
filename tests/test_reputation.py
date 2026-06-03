"""Tests for reputation algorithm v1."""

import pytest
from datetime import datetime, timedelta
from peerpedia_core.protocol import ReputationVector, IdentityType
from peerpedia_core.reputation import ReputationV1, ReputationParams


class TestReputationV1:

    def test_no_decay_for_active_user(self):
        algo = ReputationV1()
        vec = ReputationVector(
            user_id="u1",
            academic_contribution=50.0,
            review_quality=50.0,
            collaboration_spirit=50.0,
            education_outreach=50.0,
        )
        yesterday = datetime.utcnow() - timedelta(days=1)
        result = algo.apply_decay(vec, yesterday)
        assert result.academic_contribution == 50.0

    def test_decay_after_grace_period(self):
        algo = ReputationV1()
        vec = ReputationVector(
            user_id="u1",
            academic_contribution=100.0,
            review_quality=100.0,
            collaboration_spirit=100.0,
            education_outreach=100.0,
        )
        # 100 days inactive: 10 days of decay
        inactive_since = datetime.utcnow() - timedelta(days=100)
        result = algo.apply_decay(vec, inactive_since)

        # After 10 days of 0.1% daily decay: 100 * 0.999^10 ≈ 99.0
        assert result.academic_contribution < 100.0
        assert result.academic_contribution > 98.0

    def test_identity_bonus(self):
        algo = ReputationV1()
        vec = ReputationVector(user_id="u1")
        result = algo.merge_identities(vec, verified_count=2)
        # 2 * 5.0 = 10.0 base reputation
        assert result.academic_contribution == 10.0

    def test_identity_bonus_capped_at_100(self):
        algo = ReputationV1()
        vec = ReputationVector(user_id="u1", academic_contribution=95.0)
        result = algo.merge_identities(vec, verified_count=3)
        assert result.academic_contribution == 100.0  # capped


class TestReputationParams:

    def test_default_params(self):
        params = ReputationParams()
        assert params.decay_grace_days == 90
        assert params.decay_rate_per_day == 0.001
        assert params.identity_weights[IdentityType.ORCID] == 1.0  # type: ignore
        assert params.identity_weights[IdentityType.GITHUB] == 0.3  # type: ignore

    def test_change_type_weights(self):
        params = ReputationParams()
        assert params.change_type_weights["new_theorem"] == 5.0
        assert params.change_type_weights["format"] == 0.3
