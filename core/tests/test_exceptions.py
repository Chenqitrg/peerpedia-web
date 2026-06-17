# SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
# SPDX-License-Identifier: CC-BY-NC-SA-4.0

"""Tests for semantic exception classes."""

from peerpedia_core.exceptions import (
    BadRequest,
    Conflict,
    NotAuthorized,
    NotFound,
    PeerpediaError,
)


class TestPeerpediaError:
    def test_base_error_stores_detail(self):
        e = PeerpediaError("something went wrong")
        assert e.detail == "something went wrong"

    def test_base_error_detail_defaults_to_empty(self):
        e = PeerpediaError()
        assert e.detail == ""

    def test_subclass_inherits_from_base(self):
        assert issubclass(NotFound, PeerpediaError)
        assert issubclass(NotAuthorized, PeerpediaError)
        assert issubclass(Conflict, PeerpediaError)
        assert issubclass(BadRequest, PeerpediaError)

    def test_subclass_instance_is_peerpedia_error(self):
        for cls in [NotFound, NotAuthorized, Conflict, BadRequest]:
            assert isinstance(cls("test"), PeerpediaError)


class TestSemanticNames:
    """Semantic exceptions must carry no HTTP concepts in their names."""

    def test_no_status_code_attribute(self):
        """None of the semantic exceptions should have a status_code."""
        for cls in [NotFound, NotAuthorized, Conflict, BadRequest]:
            e = cls("test")
            assert not hasattr(e, "status_code"), (
                f"{cls.__name__} should not have status_code"
            )
