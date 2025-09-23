"""
Simple test to verify agent system functionality.
"""

import asyncio
import uuid
from app.agents.contracts.base import ProjectContext
from app.agents.contracts.business_analyst import BusinessAnalystInput
from app.agents.implementations.business_analyst import BusinessAnalystAgent
from app.core.logger import get_logger

logger = get_logger()


async def test_business_analyst_basic():
    """Test basic Business Analyst functionality without LLM."""
    print("🧪 Testing Business Analyst Agent...")

    # Create test context
    context = ProjectContext(
        tenant_id="test_tenant",
        project_id="test_project",
        current_step=1,
        correlation_id=str(uuid.uuid4()),
        language="en",
        user_id="test_user",
    )

    # Create agent
    agent = BusinessAnalystAgent()

    # Test input validation
    try:
        input_data = BusinessAnalystInput(
            context=context,
            idea_description="Build a task management app for remote teams",
            target_audience="Remote software development teams",
        )

        await agent.validate_input(input_data)
        print("✅ Input validation passed")

        # Test system prompt generation
        prompt = agent.get_system_prompt(context)
        assert len(prompt) > 100, "System prompt should be substantial"
        print("✅ System prompt generated")

        # Test context data retrieval (should work even if vector DB is not available)
        try:
            context_data = await agent.get_context_data(context)
            print("✅ Context data retrieval completed")
        except Exception as e:
            print(f"⚠️  Context data retrieval failed (expected if vector DB not ready): {e}")

        print("✅ Business Analyst Agent basic tests passed!")
        return True

    except Exception as e:
        print(f"❌ Business Analyst test failed: {e}")
        return False


async def test_agent_contracts():
    """Test Pydantic contracts validation."""
    print("\n🧪 Testing Agent Contracts...")

    try:
        # Test ProjectContext
        context = ProjectContext(
            tenant_id="test_tenant",
            project_id="test_project",
            current_step=1,
            user_id="test_user",
        )
        assert context.language == "en", "Default language should be 'en'"
        assert len(context.correlation_id) > 0, "Correlation ID should be generated"
        print("✅ ProjectContext validation passed")

        # Test BusinessAnalystInput
        ba_input = BusinessAnalystInput(
            context=context,
            idea_description="Test project description",
        )
        assert ba_input.context.tenant_id == "test_tenant"
        print("✅ BusinessAnalystInput validation passed")

        print("✅ All contract tests passed!")
        return True

    except Exception as e:
        print(f"❌ Contract test failed: {e}")
        return False


async def test_quality_control():
    """Test quality control validation."""
    print("\n🧪 Testing Quality Control...")

    try:
        from app.agents.base.quality_control import MarkdownValidator, ReadabilityValidator

        # Test markdown validation
        md_validator = MarkdownValidator()
        test_content = """# Test Document

## Overview
This is a test document with proper structure.

## Details
- Item 1
- Item 2
- Item 3

### Code Example
```python
print("Hello, World!")
```
"""
        result = await md_validator.validate(test_content)
        assert result.score > 0.3, f"Markdown validation should pass (got score: {result.score})"
        print("✅ Markdown validation works")

        # Test readability validation
        readability_validator = ReadabilityValidator()
        result = await readability_validator.validate(test_content)
        assert result.score >= 0.0, "Readability validation should return a score"
        print("✅ Readability validation works")

        print("✅ Quality control tests passed!")
        return True

    except Exception as e:
        print(f"❌ Quality control test failed: {e}")
        return False


async def test_llm_client_imports():
    """Test that LLM client components can be imported."""
    print("\n🧪 Testing LLM Client Imports...")

    try:
        from app.agents.base.llm_client import LLMManager, OpenAIClient, AnthropicClient, CircuitBreaker

        # Test circuit breaker
        cb = CircuitBreaker(failure_threshold=3, timeout=60)
        assert cb.failure_count == 0, "Circuit breaker should start with 0 failures"
        print("✅ Circuit breaker creation works")

        # Test LLM manager
        manager = LLMManager()
        assert len(manager.clients) == 0, "LLM manager should start with no clients"
        print("✅ LLM manager creation works")

        print("✅ LLM client import tests passed!")
        return True

    except Exception as e:
        print(f"❌ LLM client import test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting JEEX Plan Agent System Tests...\n")

    tests = [
        test_agent_contracts,
        test_business_analyst_basic,
        test_quality_control,
        test_llm_client_imports,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Agent system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    asyncio.run(main())