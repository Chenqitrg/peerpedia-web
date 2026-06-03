"""API routes for users, identities, and reputation."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticBaseModel, Field

from peerpedia.web.db_session import get_db_session
from peerpedia_core.storage.db import (
    create_user as db_create_user,
    get_user,
    create_identity as db_create_identity,
    get_identities_for_user,
)


class UserCreateRequest(PydanticBaseModel):
    id: str
    name: str
    email: str
    affiliation: str | None = None
    expertise: list[str] = Field(default_factory=list)
    bio: str | None = None


class IdentityCreateRequest(PydanticBaseModel):
    type: str
    value: str
    verified: bool = False


router = APIRouter()


@router.get("/users/{user_id}")
async def api_get_user(user_id: str):
    """Get user profile with identities."""
    session = get_db_session()
    try:
        user = get_user(session, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        identities = get_identities_for_user(session, user_id)
        result = user.to_dict()
        result["identities"] = [i.to_dict() for i in identities]
        return result
    finally:
        session.close()


@router.post("/users")
async def api_create_user(req: UserCreateRequest):
    """Create (register) a new user."""
    session = get_db_session()
    try:
        existing = get_user(session, req.id)
        if existing is not None:
            raise HTTPException(status_code=409, detail=f"User '{req.id}' already exists")
        user = db_create_user(
            session,
            id=req.id,
            name=req.name,
            email=req.email,
            affiliation=req.affiliation,
            expertise=req.expertise,
            bio=req.bio,
        )
        session.commit()
        return user.to_dict()
    finally:
        session.close()


@router.post("/users/{user_id}/identities")
async def api_create_identity(user_id: str, req: IdentityCreateRequest):
    """Bind a verified identity to a user."""
    session = get_db_session()
    try:
        user = get_user(session, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        weight_map = {
            "orcid": 100, "inst_email": 80, "arxiv": 60,
            "scholar": 50, "github": 30,
        }
        trust_weight_scaled = weight_map.get(req.type, 10)

        identity = db_create_identity(
            session,
            user_id=user_id,
            type=req.type,
            value=req.value,
            verified=req.verified,
            trust_weight=trust_weight_scaled,
        )
        session.commit()
        return identity.to_dict()
    finally:
        session.close()


@router.get("/users/{user_id}/reputation")
async def api_get_user_reputation(user_id: str):
    """Get the reputation vector for a user."""
    from peerpedia_core.reputation import ReputationV1

    session = get_db_session()
    try:
        algo = ReputationV1()
        vec = algo.compute(user_id, session=session)
        return vec.model_dump()
    finally:
        session.close()
