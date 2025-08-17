from aiogram import Router


def make_root_router() -> Router:
    from .basic import basic_router
    from .profile import profile_router
    from .meal import meal_router
    from .coach import coach_router
    from .stats import stats_router
    from .settings import settings_router

    router = Router()
    router.include_router(basic_router)
    router.include_router(profile_router)
    router.include_router(meal_router)
    router.include_router(coach_router)
    router.include_router(stats_router)
    router.include_router(settings_router)
    return router


