from pathlib import Path
from typing import Optional, Sequence, Type, cast

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.chat import MessageLikeRepresentation
from langchain_core.runnables import RunnableBinding, RunnableSequence
from pydantic import AnyUrl
from pyfakefs.fake_filesystem import FakeFilesystem

from ai_gateway.chains import (
    Chain,
    ChainRegistered,
    CustomModelsChainRegistry,
    LocalChainRegistry,
)
from ai_gateway.chains.config import (
    ChainConfig,
    ChatAnthropicParams,
    ChatLiteLLMParams,
    ModelClassProvider,
    ModelConfig,
)
from ai_gateway.chains.registry import TypeModelFactory
from ai_gateway.chains.typing import ModelMetadata


class MockChainClass(Chain):
    pass


@pytest.fixture
def mock_fs(fs: FakeFilesystem):
    chains_definitions_dir = (
        Path(__file__).parent.parent.parent / "ai_gateway" / "chains" / "definitions"
    )
    fs.create_file(
        chains_definitions_dir / "test" / "base.yml",
        contents="""
---
name: Test chain
model:
  name: claude-2.1
  params:
    model_class_provider: litellm
    timeout: 100.
    top_p: 0.1
    top_k: 50
    max_tokens: 256
    max_retries: 10
    custom_llm_provider: vllm
unit_primitives:
  - explain_code
prompt_template:
  system: Template1
""",
    )
    fs.create_file(
        chains_definitions_dir / "chat" / "react.yml",
        contents="""
---
name: Chat react chain
model:
  name: claude-3-haiku-20240307
  params:
    model_class_provider: anthropic
    temperature: 0.1
    timeout: 60
    top_p: 0.8
    top_k: 40
    max_tokens: 256
    max_retries: 6
    default_headers:
      header1: "Header1 value"
      header2: "Header2 value"
unit_primitives:
  - duo_chat
prompt_template:
  system: Template1
  user: Template2
stop:
  - Foo
  - Bar
""",
    )
    fs.create_file(
        chains_definitions_dir / "chat" / "react-custom.yml",
        contents="""
---
name: Chat react custom chain
model:
  name: custom
  params:
    model_class_provider: litellm
    temperature: 0.1
    timeout: 60
    top_p: 0.8
    top_k: 40
    max_tokens: 256
    max_retries: 6
unit_primitives:
  - duo_chat
prompt_template:
  system: Template1
  user: Template2
stop:
  - Foo
  - Bar
""",
    )
    yield fs


@pytest.fixture
def model_factories():
    yield {
        ModelClassProvider.ANTHROPIC: lambda model, **kwargs: ChatAnthropic(model=model, **kwargs),  # type: ignore[call-arg]
        ModelClassProvider.LITE_LLM: lambda model, **kwargs: ChatLiteLLM(
            model=model, **kwargs
        ),
    }


@pytest.fixture
def chains_registered():
    yield {
        "test/base": ChainRegistered(
            klass=Chain,
            config=ChainConfig(
                name="Test chain",
                model=ModelConfig(
                    name="claude-2.1",
                    params=ChatLiteLLMParams(
                        model_class_provider=ModelClassProvider.LITE_LLM,
                        timeout=100.0,
                        top_p=0.1,
                        top_k=50,
                        max_tokens=256,
                        max_retries=10,
                        custom_llm_provider="vllm",
                    ),
                ),
                unit_primitives=["explain_code"],
                prompt_template={"system": "Template1"},
            ),
        ),
        "chat/react": ChainRegistered(
            klass=MockChainClass,
            config=ChainConfig(
                name="Chat react chain",
                model=ModelConfig(
                    name="claude-3-haiku-20240307",
                    provider="anthropic",
                    params=ChatAnthropicParams(
                        model_class_provider=ModelClassProvider.ANTHROPIC,
                        temperature=0.1,
                        timeout=60,
                        top_p=0.8,
                        top_k=40,
                        max_tokens=256,
                        max_retries=6,
                        default_headers={
                            "header1": "Header1 value",
                            "header2": "Header2 value",
                        },
                    ),
                ),
                unit_primitives=["duo_chat"],
                prompt_template={"system": "Template1", "user": "Template2"},
                stop=["Foo", "Bar"],
            ),
        ),
        "chat/react-custom": ChainRegistered(
            klass=MockChainClass,
            config=ChainConfig(
                name="Chat react custom chain",
                model=ModelConfig(
                    name="custom",
                    provider="litellm",
                    params=ChatLiteLLMParams(
                        model_class_provider=ModelClassProvider.LITE_LLM,
                        temperature=0.1,
                        timeout=60,
                        top_p=0.8,
                        top_k=40,
                        max_tokens=256,
                        max_retries=6,
                    ),
                ),
                unit_primitives=["duo_chat"],
                prompt_template={"system": "Template1", "user": "Template2"},
                stop=["Foo", "Bar"],
            ),
        ),
    }


class TestLocalChainRegistry:
    def test_from_local_yaml(
        self,
        mock_fs: FakeFilesystem,
        model_factories: dict[ModelClassProvider, TypeModelFactory],
        chains_registered: dict[str, ChainRegistered],
    ):
        registry = LocalChainRegistry.from_local_yaml(
            class_overrides={
                "chat/react": MockChainClass,
                "chat/react-custom": MockChainClass,
            },
            model_factories=model_factories,
        )

        assert registry.chains_registered == chains_registered

    @pytest.mark.parametrize(
        (
            "chain_id",
            "expected_name",
            "expected_class",
            "expected_messages",
            "expected_model",
            "expected_kwargs",
            "expected_model_params",
        ),
        [
            (
                "test",
                "Test chain",
                Chain,
                [("system", "Template1")],
                "claude-2.1",
                None,
                None,
            ),
            (
                "test/base",
                "Test chain",
                Chain,
                [("system", "Template1")],
                "claude-2.1",
                None,
                {
                    "request_timeout": 100.0,  # accessed by alias
                    "top_p": 0.1,
                    "top_k": 50,
                    "max_tokens": 256,
                    "max_retries": 10,
                    "custom_llm_provider": "vllm",
                },
            ),
            (
                "chat/react",
                "Chat react chain",
                MockChainClass,
                [("system", "Template1"), ("user", "Template2")],
                "claude-3-haiku-20240307",
                {"stop": ["Foo", "Bar"]},
                {
                    "temperature": 0.1,
                    "default_request_timeout": 60,  # accessed by alias
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_tokens": 256,
                    "max_retries": 6,
                    "default_headers": {
                        "header1": "Header1 value",
                        "header2": "Header2 value",
                    },
                },
            ),
        ],
    )
    def test_get(
        self,
        chains_registered: dict[str, ChainRegistered],
        model_factories: dict[ModelClassProvider, TypeModelFactory],
        chain_id: str,
        expected_name: str,
        expected_class: Type[Chain],
        expected_messages: Sequence[MessageLikeRepresentation],
        expected_model: str,
        expected_kwargs: dict,
        expected_model_params: dict | None,
    ):
        registry = LocalChainRegistry(
            model_factories=model_factories,
            chains_registered=chains_registered,
        )

        chain = registry.get(chain_id, {}, None)

        sequence = cast(RunnableSequence, chain.bound)
        actual_messages = cast(ChatPromptTemplate, sequence.first).messages
        actual_model = cast(RunnableBinding, sequence.last)

        assert chain.name == expected_name
        assert isinstance(chain, expected_class)
        assert (
            actual_messages
            == ChatPromptTemplate.from_messages(expected_messages).messages
        )
        assert actual_model.model == expected_model

        if expected_kwargs:
            assert actual_model.kwargs == expected_kwargs

        actual_model = (
            actual_model.bound if getattr(actual_model, "bound", None) else actual_model  # type: ignore[assignment]
        )
        if expected_model_params:
            actual_model_params = {
                key: value
                for key, value in dict(actual_model).items()
                if key in expected_model_params
            }
            assert actual_model_params == expected_model_params


class TestCustomModelsChainRegistry:
    def test_from_local_yaml(
        self,
        mock_fs: FakeFilesystem,
        model_factories: dict[ModelClassProvider, TypeModelFactory],
        chains_registered: dict[str, ChainRegistered],
    ):
        registry = LocalChainRegistry.from_local_yaml(
            class_overrides={
                "chat/react": MockChainClass,
                "chat/react-custom": MockChainClass,
            },
            model_factories=model_factories,
        )

        assert registry.chains_registered == chains_registered

    @pytest.mark.parametrize(
        (
            "chain_id",
            "model_metadata",
            "expected_name",
            "expected_class",
            "expected_messages",
            "expected_model",
            "expected_kwargs",
            "expected_model_params",
        ),
        [
            (
                "chat/react",
                None,
                "Chat react chain",
                MockChainClass,
                [("system", "Template1"), ("user", "Template2")],
                "claude-3-haiku-20240307",
                {"stop": ["Foo", "Bar"]},
                {
                    "temperature": 0.1,
                    "default_request_timeout": 60,  # accessed by alias
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_tokens": 256,
                    "max_retries": 6,
                },
            ),
            (
                "chat/react",
                ModelMetadata(
                    name="mistral",
                    endpoint=cast(AnyUrl, "http://localhost:4000/"),
                    api_key="token",
                    provider="openai",
                ),
                "Chat react custom chain",
                MockChainClass,
                [("system", "Template1"), ("user", "Template2")],
                "custom",
                {
                    "stop": ["Foo", "Bar"],
                    "model": "mistral",
                    "custom_llm_provider": "openai",
                    "api_key": "token",
                    "api_base": "http://localhost:4000/",
                },
                {
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_tokens": 256,
                    "max_retries": 6,
                },
            ),
        ],
    )
    def test_get(
        self,
        chains_registered: dict[str, ChainRegistered],
        model_factories: dict[ModelClassProvider, TypeModelFactory],
        chain_id: str,
        model_metadata: Optional[ModelMetadata],
        expected_name: str,
        expected_class: Type[Chain],
        expected_messages: Sequence[MessageLikeRepresentation],
        expected_model: str,
        expected_kwargs: dict,
        expected_model_params: dict | None,
    ):
        registry = CustomModelsChainRegistry(
            model_factories=model_factories,
            chains_registered=chains_registered,
        )

        chain = registry.get(chain_id, {}, model_metadata)

        sequence = cast(RunnableSequence, chain.bound)
        actual_messages = cast(ChatPromptTemplate, sequence.first).messages
        actual_model = cast(RunnableBinding, sequence.last)

        assert chain.name == expected_name
        assert isinstance(chain, expected_class)
        assert (
            actual_messages
            == ChatPromptTemplate.from_messages(expected_messages).messages
        )
        assert actual_model.model == expected_model

        if expected_kwargs:
            assert actual_model.kwargs == expected_kwargs

        actual_model = (
            actual_model.bound if getattr(actual_model, "bound", None) else actual_model  # type: ignore[assignment]
        )
        if expected_model_params:
            actual_model_params = {
                key: value
                for key, value in dict(actual_model).items()
                if key in expected_model_params
            }
            assert actual_model_params == expected_model_params
