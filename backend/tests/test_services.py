"""
Unit tests for service layer
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

from core.services.chat_service import UnifiedChatService
from core.services.document_service import UnifiedDocumentService
from core.services.database_service import UnifiedDatabaseService
from core.services.usage_service import UsageService
from core.exceptions import *


class TestChatService:
    """Test unified chat service"""
    
    @pytest.fixture
    def chat_service(self):
        """Create chat service instance"""
        with patch('core.services.chat_service.get_settings'):
            with patch('core.services.chat_service.OpenAI'):
                service = UnifiedChatService()
                service._initialized = True
                return service
    
    @pytest.mark.asyncio
    async def test_process_message_with_thread_strategy(self, chat_service):
        """Test processing message with thread strategy"""
        chat_service.strategies['thread'] = Mock()
        chat_service.strategies['thread'].process_message = Mock(
            return_value={
                "response": "Test response",
                "session_id": "test_session",
                "usage": {"tokens": 100}
            }
        )
        
        result = await chat_service.process_message(
            message="Test message",
            strategy="thread"
        )
        
        assert result["response"] == "Test response"
        assert result["session_id"] == "test_session"
        chat_service.strategies['thread'].process_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_invalid_strategy(self, chat_service):
        """Test processing message with invalid strategy"""
        with pytest.raises(ValueError, match="Unknown chat strategy"):
            await chat_service.process_message(
                message="Test",
                strategy="invalid"
            )
    
    def test_get_available_strategies(self, chat_service):
        """Test getting available strategies"""
        chat_service.strategies = {
            'thread': Mock(),
            'direct': Mock()
        }
        
        strategies = chat_service.get_available_strategies()
        assert 'thread' in strategies
        assert 'direct' in strategies
    
    def test_set_default_strategy(self, chat_service):
        """Test setting default strategy"""
        chat_service.strategies = {'thread': Mock()}
        chat_service.set_default_strategy('thread')
        assert chat_service.default_strategy == 'thread'
    
    def test_set_invalid_default_strategy(self, chat_service):
        """Test setting invalid default strategy"""
        with pytest.raises(ValueError):
            chat_service.set_default_strategy('invalid')


class TestDocumentService:
    """Test unified document service"""
    
    @pytest.fixture
    def doc_service(self):
        """Create document service instance"""
        with patch('core.services.document_service.get_settings'):
            with patch('core.services.document_service.OpenAI'):
                with patch('core.services.document_service.get_database_service'):
                    service = UnifiedDocumentService()
                    service._initialized = True
                    return service
    
    @pytest.mark.asyncio
    async def test_upload_document_success(self, doc_service):
        """Test successful document upload"""
        doc_service.openai_client = Mock()
        doc_service.openai_client.files.create = Mock(
            return_value=Mock(id="file_123")
        )
        doc_service.openai_client.vector_stores.file_batches.create = Mock()
        
        doc_service.db_service = Mock()
        doc_service.db_service.get_client = MagicMock()
        
        from io import BytesIO
        file = BytesIO(b"Test content")
        
        result = await doc_service.upload_document(
            file=file,
            filename="test.txt",
            user_id="user_123"
        )
        
        assert result["filename"] == "test.txt"
        assert result["status"] == "uploaded"
    
    @pytest.mark.asyncio
    async def test_list_documents(self, doc_service):
        """Test listing documents"""
        doc_service.db_service = Mock()
        doc_service.db_service.get_client = MagicMock()
        
        mock_client = MagicMock()
        mock_result = Mock()
        mock_result.data = [
            {"id": "1", "filename": "doc1.txt"},
            {"id": "2", "filename": "doc2.pdf"}
        ]
        
        mock_client.table().select().execute.return_value = mock_result
        doc_service.db_service.get_client().__enter__.return_value = mock_client
        
        docs = await doc_service.list_documents(limit=10)
        assert len(docs) == 2
        assert docs[0]["filename"] == "doc1.txt"
    
    @pytest.mark.asyncio
    async def test_delete_document(self, doc_service):
        """Test deleting document"""
        doc_service.openai_client = Mock()
        doc_service.openai_client.files.delete = Mock()
        
        doc_service.db_service = Mock()
        doc_service.db_service.get_client = MagicMock()
        
        # Mock get document
        mock_client = MagicMock()
        mock_result = Mock()
        mock_result.data = [{"id": "1", "openai_file_id": "file_123"}]
        
        mock_client.table().select().eq().single().execute.return_value = mock_result
        mock_client.table().delete().eq().execute.return_value = Mock(data=[{"id": "1"}])
        doc_service.db_service.get_client().__enter__.return_value = mock_client
        
        result = await doc_service.delete_document("1")
        assert result is True
        doc_service.openai_client.files.delete.assert_called_once_with("file_123")


class TestDatabaseService:
    """Test unified database service"""
    
    def test_singleton_pattern(self):
        """Test that database service follows singleton pattern"""
        with patch('core.services.database_service.get_settings'):
            with patch('core.services.database_service.create_client'):
                service1 = UnifiedDatabaseService()
                service2 = UnifiedDatabaseService()
                assert service1 is service2
    
    def test_get_client(self):
        """Test getting database client"""
        with patch('core.services.database_service.get_settings'):
            with patch('core.services.database_service.create_client') as mock_create:
                mock_client = Mock()
                mock_create.return_value = mock_client
                
                service = UnifiedDatabaseService()
                client = service.get_client()
                assert client == mock_client
    
    def test_sign_in_with_password(self):
        """Test sign in with password"""
        with patch('core.services.database_service.get_settings'):
            with patch('core.services.database_service.create_client') as mock_create:
                mock_client = Mock()
                mock_auth = Mock()
                mock_client.auth = mock_auth
                mock_auth.sign_in_with_password.return_value = Mock(
                    session={"access_token": "token"},
                    user={"id": "user_123"}
                )
                mock_create.return_value = mock_client
                
                service = UnifiedDatabaseService()
                result = service.sign_in_with_password("test@example.com", "password")
                
                assert result["session"]["access_token"] == "token"
                mock_auth.sign_in_with_password.assert_called_once()


class TestUsageService:
    """Test usage tracking service"""
    
    @pytest.fixture
    def usage_service(self):
        """Create usage service instance"""
        with patch('core.services.usage_service.get_settings'):
            with patch('core.services.usage_service.get_database_service'):
                service = UsageService()
                service._initialized = True
                return service
    
    def test_track_usage(self, usage_service):
        """Test tracking usage"""
        usage_service.db_service = Mock()
        usage_service.db_service.get_client = MagicMock()
        
        mock_client = MagicMock()
        mock_result = Mock()
        mock_result.data = [{"id": "1"}]
        
        mock_client.table().insert().execute.return_value = mock_result
        usage_service.db_service.get_client().__enter__.return_value = mock_client
        
        result = usage_service.track_usage(
            user_id="user_123",
            session_id="session_123",
            tokens_used=100
        )
        
        assert result is True
    
    def test_get_usage_summary(self, usage_service):
        """Test getting usage summary"""
        usage_service.db_service = Mock()
        usage_service.db_service.get_client = MagicMock()
        
        mock_client = MagicMock()
        mock_result = Mock()
        mock_result.data = [
            {"tokens_used": 100, "session_id": "s1", "model": "gpt-4", "operation": "chat"},
            {"tokens_used": 50, "session_id": "s1", "model": "gpt-4", "operation": "chat"},
            {"tokens_used": 75, "session_id": "s2", "model": "gpt-3.5", "operation": "document"}
        ]
        
        mock_client.table().select().execute.return_value = mock_result
        usage_service.db_service.get_client().__enter__.return_value = mock_client
        
        summary = usage_service.get_usage_summary()
        
        assert summary["total_tokens"] == 225
        assert summary["total_sessions"] == 2
        assert summary["model_usage"]["gpt-4"] == 150
        assert summary["operation_counts"]["chat"] == 2
    
    def test_get_user_quota(self, usage_service):
        """Test getting user quota"""
        with patch.object(usage_service, 'get_usage_summary') as mock_summary:
            mock_summary.side_effect = [
                {"total_tokens": 50000, "total_operations": 100},  # Monthly
                {"total_tokens": 5000, "total_operations": 50}     # Daily
            ]
            
            quota = usage_service.get_user_quota("user_123")
            
            assert quota["quota"]["monthly_tokens"] == 1000000
            assert quota["usage"]["monthly_tokens"] == 50000
            assert quota["remaining"]["tokens"] == 950000
            assert quota["remaining"]["operations"] == 950


class TestExceptions:
    """Test custom exceptions"""
    
    def test_rag_exception_to_dict(self):
        """Test converting exception to dictionary"""
        exc = RAGException(
            message="Test error",
            error_code="TEST_ERROR",
            details={"field": "value"}
        )
        
        result = exc.to_dict()
        assert result["success"] is False
        assert result["error"] == "Test error"
        assert result["error_code"] == "TEST_ERROR"
        assert result["details"]["field"] == "value"
    
    def test_authentication_error(self):
        """Test authentication error"""
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert exc.error_code == ErrorCode.AUTH_REQUIRED
    
    def test_validation_error(self):
        """Test validation error"""
        exc = ValidationError("email", "Invalid format")
        assert exc.status_code == 422
        assert "email" in exc.message
        assert exc.details["field"] == "email"
    
    def test_quota_exceeded_error(self):
        """Test quota exceeded error"""
        exc = QuotaExceededError("tokens", 1000, 1500)
        assert exc.status_code == 429
        assert exc.details["limit"] == 1000
        assert exc.details["current"] == 1500