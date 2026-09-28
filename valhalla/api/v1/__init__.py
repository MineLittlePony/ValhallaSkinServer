from fastapi import APIRouter

from . import auth, bulk, history, legacy, textures, user
from .graphql import graphql

router = APIRouter()
router.include_router(auth.router)
router.include_router(bulk.router)
router.include_router(history.router)
router.include_router(legacy.router)
router.include_router(textures.router)
router.include_router(user.router)

router.include_router(graphql)
