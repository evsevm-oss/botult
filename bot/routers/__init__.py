from aiogram import Router


def make_root_router() -> Router:
    from .basic import basic_router

    router = Router()
    router.include_router(basic_router)
    return router


