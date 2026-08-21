from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.user import UserCreate, UserRead

router = APIRouter(
    tags=["Users"],
)


@router.post(
    "/tenants/{tenant_id}/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    tenant_id: UUID,
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    user = User(
        tenant_id=tenant_id,
        email=payload.email,
        full_name=payload.full_name,
    )

    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists in this tenant.",
        ) from None

    await db.refresh(user)

    return user


@router.get(
    "/tenants/{tenant_id}/users",
    response_model=list[UserRead],
)
async def list_users(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id).order_by(User.created_at)
    )

    return result.scalars().all()


@router.get(
    "/users/{user_id}",
    response_model=UserRead,
)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user
