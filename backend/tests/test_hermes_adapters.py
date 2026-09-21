# -*- coding: utf-8 -*-
# Copyright (c) 2026 吕博旺 (131025199403304817). All rights reserved.
"""Hermes External System Adapters Integration Tests.

测试 Trade AI Agent 和 GoodJob CRM 适配器的集成功能。
验证适配器能够正确连接外部系统并执行编排任务。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.services.hermes.executors.trade_ai_agent_executor import TradeAiAgentExecutor
from app.services.hermes.executors.goodjob_crm_executor import GoodJobCrmExecutor
from app.services.hermes.executors.base import ExecutorContext, ExecutorRegistry
from app.schemas.hermes_orchestration import TaskNode


class TestTradeAiAgentExecutor:
    """Trade AI Agent 适配器测试"""

    @pytest.fixture
    def executor(self):
        """创建适配器实例"""
        return TradeAiAgentExecutor(base_url="http://test.example.com")

    @pytest.fixture
    def mock_context(self):
        """模拟执行上下文"""
        db = Mock(spec=Session)
        return ExecutorContext(
            db=db,
            tenant_id="test_tenant",
            plan_id="test_plan_123"
        )

    @pytest.fixture
    def sample_task_node(self):
        """示例任务节点"""
        return TaskNode(
            id="node_1",
            capability="prospect.scrape",
            input={
                "region": "middle_east",
                "keywords": ["construction materials", "building supplies"],
                "intent_criteria": "high_purchase_intent"
            },
            sop_ref="",
            depends_on=[]
        )

    def test_executor_name(self, executor):
        """测试执行器名称"""
        assert executor.get_executor_name() == "trade_ai_agent"

    def test_get_capabilities(self, executor):
        """测试能力声明"""
        capabilities = executor.get_capabilities()
        
        # 验证关键能力存在
        assert "prospect.scrape" in capabilities
        assert "outreach.whatsapp" in capabilities
        assert "outreach.email" in capabilities
        assert "inbox.classify" in capabilities
        
        # 验证能力元数据完整
        prospect_cap = capabilities["prospect.scrape"]
        assert "desc" in prospect_cap
        assert "input" in prospect_cap
        assert "output" in prospect_cap
        assert "cost" in prospect_cap
        assert "needs_approval" in prospect_cap

    @patch('requests.post')
    async def test_successful_execution(self, mock_post, executor, mock_context, sample_task_node):
        """测试成功执行场景"""
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "prospects": [
                    {"id": "prospect_1", "company": "ABC Corp", "country": "UAE"},
                    {"id": "prospect_2", "company": "XYZ LLC", "country": "KSA"}
                ],
                "count": 2,
                "scrape_metadata": {"timestamp": "2026-09-20T10:00:00Z"}
            }
        }
        mock_post.return_value = mock_response

        # 执行任务
        result = await executor.run(sample_task_node, mock_context)

        # 验证结果
        assert result.status == "succeeded"
        assert result.output["count"] == 2
        assert len(result.output["prospects"]) == 2
        
        # 验证 API 调用
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "prospect.scrape" in call_args[0][0]  # URL 包含端点
        assert call_args[1]["json"]["region"] == "middle_east"
        assert call_args[1]["json"]["tenant_id"] == "test_tenant"

    @patch('requests.post')
    async def test_timeout_handling(self, mock_post, executor, mock_context, sample_task_node):
        """测试超时处理"""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        result = await executor.run(sample_task_node, mock_context)

        assert result.status == "failed"
        assert "timeout" in result.error.lower()

    @patch('requests.post')
    async def test_connection_error_handling(self, mock_post, executor, mock_context, sample_task_node):
        """测试连接错误处理"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError()

        result = await executor.run(sample_task_node, mock_context)

        assert result.status == "failed"
        assert "connect" in result.error.lower()

    @patch('requests.post')
    async def test_unknown_capability(self, mock_post, executor, mock_context):
        """测试未知能力处理"""
        unknown_node = TaskNode(
            id="node_1",
            capability="unknown.capability",
            input={},
            sop_ref="",
            depends_on=[]
        )

        result = await executor.run(unknown_node, mock_context)

        assert result.status == "failed"
        assert "Unknown capability" in result.error

    @patch('requests.post')
    async def test_business_logic_failure(self, mock_post, executor, mock_context, sample_task_node):
        """测试业务逻辑失败处理"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": False,
            "error": "Insufficient credits for scraping operation"
        }
        mock_post.return_value = mock_response

        result = await executor.run(sample_task_node, mock_context)

        assert result.status == "failed"
        assert "Insufficient credits" in result.error


class TestGoodJobCrmExecutor:
    """GoodJob CRM 适配器测试"""

    @pytest.fixture
    def executor(self):
        """创建适配器实例"""
        return GoodJobCrmExecutor(
            base_url="http://test.goodjob.com",
            whatsapp_url="http://test.whatsapp.com"
        )

    @pytest.fixture
    def mock_context(self):
        """模拟执行上下文"""
        db = Mock(spec=Session)
        return ExecutorContext(
            db=db,
            tenant_id="test_tenant",
            plan_id="test_plan_456"
        )

    @pytest.fixture
    def sample_deal_node(self):
        """示例商机节点"""
        return TaskNode(
            id="node_2",
            capability="deal.create",
            input={
                "customer_id": "customer_123",
                "inquiry_source": "website",
                "initial_stage": "inquiry",
                "description": "Request for LED lighting products"
            },
            sop_ref="",
            depends_on=[]
        )

    @pytest.fixture
    def sample_pi_node(self):
        """示例 PI 生成节点"""
        return TaskNode(
            id="node_3",
            capability="pi.generate",
            input={
                "deal_id": "deal_456",
                "language": "en",
                "currency": "USD",
                "incoterms": "FOB",
                "items": [
                    {
                        "product_id": "prod_001",
                        "description": "LED Flood Light 200W",
                        "quantity": 100,
                        "unit_price": 25.50
                    }
                ]
            },
            sop_ref="",
            depends_on=[]
        )

    def test_executor_name(self, executor):
        """测试执行器名称"""
        assert executor.get_executor_name() == "goodjob_crm"

    def test_get_capabilities(self, executor):
        """测试能力声明"""
        capabilities = executor.get_capabilities()
        
        # 验证关键能力存在
        assert "deal.create" in capabilities
        assert "deal.advance" in capabilities
        assert "pi.generate" in capabilities
        assert "pi.send_whatsapp" in capabilities
        assert "trade_docs.generate" in capabilities
        assert "whatsapp.translate" in capabilities
        
        # 验证外贸7步履约状态映射
        deal_advance_cap = capabilities["deal.advance"]
        assert "desc" in deal_advance_cap
        assert deal_advance_cap["needs_approval"] == True  # 状态变更需人工确认

    @patch('requests.post')
    async def test_successful_deal_creation(self, mock_post, executor, mock_context, sample_deal_node):
        """测试成功创建商机"""
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "deal_id": "deal_789",
                "deal_number": "DEAL-2026-0920",
                "stage": "inquiry",
                "created_at": "2026-09-20T10:30:00Z"
            }
        }
        mock_post.return_value = mock_response

        # 执行任务
        result = await executor.run(sample_deal_node, mock_context)

        # 验证结果
        assert result.status == "succeeded"
        assert result.output["deal_id"] == "deal_789"
        assert result.output["stage"] == "inquiry"
        
        # 验证 API 调用
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/api/deals" in call_args[0][0]
        assert call_args[1]["json"]["customer_id"] == "customer_123"

    @patch('requests.post')
    async def test_successful_pi_generation(self, mock_post, executor, mock_context, sample_pi_node):
        """测试成功生成 PI"""
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "pi_id": "pi_2026_0847",
                "pi_number": "PI-2026-0847",
                "pdf_url": "https://storage.example.com/pi/PI-2026-0847.pdf",
                "grand_total": 2550.00,
                "valid_until": "2026-10-20"
            }
        }
        mock_post.return_value = mock_response

        # 执行任务
        result = await executor.run(sample_pi_node, mock_context)

        # 验证结果
        assert result.status == "succeeded"
        assert result.output["pi_number"] == "PI-2026-0847"
        assert result.output["grand_total"] == 2550.00

    @patch('requests.post')
    async def test_path_parameter_resolution(self, mock_post, executor, mock_context):
        """测试路径参数解析"""
        deal_advance_node = TaskNode(
            id="node_4",
            capability="deal.advance",
            input={
                "deal_id": "deal_999",
                "target_stage": "quoted",
                "transition_reason": "Customer confirmed price"
            },
            sop_ref="",
            depends_on=[]
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_post.return_value = mock_response

        await executor.run(deal_advance_node, mock_context)

        # 验证路径参数正确解析
        call_args = mock_post.call_args
        assert "/api/deals/deal_999/advance" in call_args[0][0]

    @patch('requests.post')
    async def test_whatsapp_service_routing(self, mock_post, executor, mock_context):
        """测试 WhatsApp 服务路由"""
        whatsapp_node = TaskNode(
            id="node_5",
            capability="whatsapp.translate",
            input={
                "message_id": "msg_123",
                "source_language": "ar",
                "target_language": "zh",
                "content": "مرحبا"
            },
            sop_ref="",
            depends_on=[]
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_post.return_value = mock_response

        await executor.run(whatsapp_node, mock_context)

        # 验证调用 WhatsApp Plugin 服务
        call_args = mock_post.call_args
        assert "test.whatsapp.com" in call_args[0][0]  # 使用 whatsapp_url
        assert "/api/whatsapp/translate" in call_args[0][0]

    @patch('requests.post')
    async def test_missing_path_parameter(self, mock_post, executor, mock_context):
        """测试缺失路径参数处理"""
        invalid_node = TaskNode(
            id="node_6",
            capability="deal.advance",
            input={
                "target_stage": "quoted",
                # 缺少 deal_id
            },
            sop_ref="",
            depends_on=[]
        )

        result = await executor.run(invalid_node, mock_context)

        assert result.status == "failed"
        assert "Missing required path parameter" in result.error


class TestExecutorRegistryIntegration:
    """执行器注册表集成测试"""

    def test_trade_ai_agent_registration(self):
        """测试 Trade AI Agent 执行器注册"""
        assert ExecutorRegistry.has("trade_ai_agent")
        executor = ExecutorRegistry.get("trade_ai_agent")
        assert isinstance(executor, TradeAiAgentExecutor)

    def test_goodjob_crm_registration(self):
        """测试 GoodJob CRM 执行器注册"""
        assert ExecutorRegistry.has("goodjob_crm")
        executor = ExecutorRegistry.get("goodjob_crm")
        assert isinstance(executor, GoodJobCrmExecutor)

    def test_capabilities_aggregation(self):
        """测试能力聚合"""
        all_caps = ExecutorRegistry.all_capabilities()
        
        # 验证 Trade AI Agent 能力
        assert "prospect.scrape" in all_caps
        assert all_caps["prospect.scrape"]["executor"] == "trade_ai_agent"
        
        # 验证 GoodJob CRM 能力
        assert "deal.create" in all_caps
        assert all_caps["deal.create"]["executor"] == "goodjob_crm"
        assert "pi.generate" in all_caps
        assert all_caps["pi.generate"]["executor"] == "goodjob_crm"

    def test_executor_list(self):
        """测试执行器列表"""
        executors = ExecutorRegistry.list_executors()
        
        assert "trade_ai_agent" in executors
        assert "goodjob_crm" in executors
        assert "accio" in executors  # 现有执行器
        assert "deerflow" in executors  # 现有执行器


class TestCapabilityValidation:
    """能力验证测试"""

    def test_trade_ai_agent_capability_completeness(self):
        """验证 Trade AI Agent 能力声明完整性"""
        executor = TradeAiAgentExecutor()
        capabilities = executor.get_capabilities()
        
        for cap_name, cap_spec in capabilities.items():
            # 每个能力必须包含基本字段
            assert "desc" in cap_spec, f"{cap_name} missing desc"
            assert "input" in cap_spec, f"{cap_name} missing input"
            assert "output" in cap_spec, f"{cap_name} missing output"
            assert "cost" in cap_spec, f"{cap_name} missing cost"
            assert "needs_approval" in cap_spec, f"{cap_name} missing needs_approval"
            
            # 成本必须包含 tokens 和 seconds
            assert "tokens" in cap_spec["cost"], f"{cap_name} cost missing tokens"
            assert "seconds" in cap_spec["cost"], f"{cap_name} cost missing seconds"

    def test_goodjob_crm_capability_completeness(self):
        """验证 GoodJob CRM 能力声明完整性"""
        executor = GoodJobCrmExecutor()
        capabilities = executor.get_capabilities()
        
        for cap_name, cap_spec in capabilities.items():
            # 每个能力必须包含基本字段
            assert "desc" in cap_spec, f"{cap_name} missing desc"
            assert "input" in cap_spec, f"{cap_name} missing input"
            assert "output" in cap_spec, f"{cap_name} missing output"
            assert "cost" in cap_spec, f"{cap_name} missing cost"
            assert "needs_approval" in cap_spec, f"{cap_name} missing needs_approval"

    def test_trade_ai_agent_approval_flags(self):
        """验证 Trade AI Agent 审批标志合理性"""
        executor = TradeAiAgentExecutor()
        capabilities = executor.get_capabilities()
        
        # 外联操作应该需要审批
        assert capabilities["outreach.whatsapp"]["needs_approval"] == True
        assert capabilities["outreach.email"]["needs_approval"] == True
        assert capabilities["workflow.trigger"]["needs_approval"] == True
        
        # 内部分析操作不需要审批
        assert capabilities["prospect.scrape"]["needs_approval"] == False
        assert capabilities["inbox.classify"]["needs_approval"] == False

    def test_goodjob_crm_approval_flags(self):
        """验证 GoodJob CRM 审批标志合理性"""
        executor = GoodJobCrmExecutor()
        capabilities = executor.get_capabilities()
        
        # 财务和法务单据需要审批
        assert capabilities["pi.generate"]["needs_approval"] == True
        assert capabilities["pi.send_whatsapp"]["needs_approval"] == True
        assert capabilities["trade_docs.generate"]["needs_approval"] == True
        
        # 状态变更需要审批
        assert capabilities["deal.advance"]["needs_approval"] == True
        
        # 基础 CRUD 不需要审批
        assert capabilities["deal.create"]["needs_approval"] == False
        assert capabilities["customer.create"]["needs_approval"] == False


# 运行测试的便捷函数
def run_adapter_tests():
    """运行适配器集成测试"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_adapter_tests()