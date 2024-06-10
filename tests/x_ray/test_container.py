from typing import cast

import pytest
from dependency_injector import containers, providers

from ai_gateway.models.anthropic import AnthropicModel


@pytest.mark.asyncio
async def test_container(mock_container: containers.DeclarativeContainer):
    x_ray = cast(providers.Container, mock_container.x_ray)

    assert isinstance(await x_ray.anthropic_claude(), AnthropicModel)
