"""
RAG Chains

Pre-built chains for Retrieval-Augmented Generation.
Combines your documents with LLM calls for context-aware responses.
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class RAGChainManager:
    """
    Manages RAG (Retrieval-Augmented Generation) chains.
    
    RAG allows you to:
    1. Load your documents into a vector store
    2. Query them semantically
    3. Pass relevant context to the LLM
    4. Get answers based on YOUR data
    """
    
    def __init__(self):
        logger.info("🔗 RAGChainManager initialized")
    
    def create_qa_chain(
        self,
        vectorstore,
        llm,
        chain_type: str = "stuff",
        **kwargs
    ):
        """
        Create a Question-Answering chain over documents.
        
        Args:
            vectorstore: Vector store containing documents
            llm: LLM instance (from your AIGovernor or LangChain)
            chain_type: Type of chain ("stuff", "map_reduce", "refine", "map_rerank")
            **kwargs: Chain-specific options
            
        Returns:
            RetrievalQA chain
        """
        try:
            from langchain.chains import RetrievalQA
        except ImportError:
            raise ImportError("RAG chains require: pip install langchain")
        
        logger.info(f"🔗 Creating QA chain (type: {chain_type})")
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type=chain_type,
            retriever=vectorstore.as_retriever(),
            return_source_documents=True,
            **kwargs
        )
        
        return qa_chain
    
    def query(
        self,
        qa_chain,
        question: str
    ) -> Dict[str, Any]:
        """
        Query the RAG chain with a question.
        
        Args:
            qa_chain: QA chain instance
            question: Question to ask
            
        Returns:
            Dict with 'result' (answer) and 'source_documents' (sources)
        """
        logger.info(f"❓ RAG Query: {question[:100]}...")
        
        result = qa_chain({"query": question})
        
        logger.info(f"✅ RAG Answer: {result['result'][:100]}...")
        
        return result
    
    def create_conversational_chain(
        self,
        vectorstore,
        llm,
        memory_key: str = "chat_history",
        **kwargs
    ):
        """
        Create a conversational RAG chain with memory.
        
        Args:
            vectorstore: Vector store containing documents
            llm: LLM instance
            memory_key: Key for storing conversation history
            **kwargs: Chain-specific options
            
        Returns:
            ConversationalRetrievalChain
        """
        try:
            from langchain.chains import ConversationalRetrievalChain
            from langchain.memory import ConversationBufferMemory
        except ImportError:
            raise ImportError("Conversational chains require: pip install langchain")
        
        logger.info(f"🔗 Creating conversational RAG chain")
        
        memory = ConversationBufferMemory(
            memory_key=memory_key,
            return_messages=True,
            output_key='answer'
        )
        
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(),
            memory=memory,
            return_source_documents=True,
            **kwargs
        )
        
        return chain
    
    def chat(
        self,
        conversational_chain,
        question: str
    ) -> Dict[str, Any]:
        """
        Chat with the conversational RAG chain (maintains history).
        
        Args:
            conversational_chain: Conversational chain instance
            question: Question to ask
            
        Returns:
            Dict with 'answer' and 'source_documents'
        """
        logger.info(f"💬 Chat: {question[:100]}...")
        
        result = conversational_chain({"question": question})
        
        logger.info(f"✅ Chat Answer: {result['answer'][:100]}...")
        
        return result


class LangChainLLMAdapter:
    """
    Adapter to use your existing AIGovernor with LangChain chains.
    
    This allows you to keep using your governor for routing/fallback
    while still leveraging LangChain's RAG features.
    """
    
    def __init__(self, ai_governor, provider: str = "openai", model: str = "gpt-4"):
        """
        Args:
            ai_governor: Your AIGovernor instance
            provider: Provider to use (openai, anthropic, etc.)
            model: Model name
        """
        self.ai_governor = ai_governor
        self.provider = provider
        self.model = model
        logger.info(f"🔌 LangChain LLM Adapter created (provider={provider}, model={model})")
    
    def __call__(self, prompt: str, **kwargs) -> str:
        """Call the LLM via your AIGovernor."""
        try:
            response = self.ai_governor.call_llm(
                prompt=prompt,
                provider=self.provider,
                model=self.model,
                **kwargs
            )
            return response.get("content", "")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def predict(self, text: str, **kwargs) -> str:
        """LangChain-compatible predict method."""
        return self(text, **kwargs)
    
    def _call(self, prompt: str, **kwargs) -> str:
        """LangChain-compatible _call method."""
        return self(prompt, **kwargs)

