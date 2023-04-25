from fastapi import APIRouter


class APIRouterBuilderV2:
    def __init__(self):
        self._router = APIRouter()
        self._router.prefix = "/v2"

    def with_generative_ai(self):
        from codesuggestions.api.v2.endpoints import generative

        self._router.include_router(generative.router)

        return self

    def with_gl_code_suggestions(self):
        from codesuggestions.api.v2.endpoints import suggestions

        self._router.include_router(suggestions.router)

        return self

    @property
    def router(self):
        return self._router
