"""
Vector Store Manager

Manages vector databases for semantic search and RAG.
Supports both local (FREE) and cloud-based vector stores.
"""

import logging
from typing import List, Optional, Dict, Any
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorStoreProvider(str, Enum):
    """Available vector store providers."""
    CHROMA = "chroma"          # FREE, local, persistent
    FAISS = "faiss"            # FREE, local, in-memory
    PINECONE = "pinecone"      # PAID, cloud, scalable
    WEAVIATE = "weaviate"      # PAID/FREE, cloud/local


class VectorStoreManager:
    """
    Manages vector stores for semantic search and RAG.
    
    Supports:
    - Chroma (FREE, local, persistent)
    - FAISS (FREE, local, in-memory, very fast)
    - Pinecone (PAID, cloud, scalable)
    - Weaviate (PAID/FREE, cloud/local)
    """
    
    def __init__(self, default_persist_dir: str = "./data/vectorstores"):
        self._vectorstores_cache: Dict[str, Any] = {}
        self.default_persist_dir = Path(default_persist_dir)
        self.default_persist_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"🗄️ VectorStoreManager initialized (persist_dir: {self.default_persist_dir})")
    
    def create_vectorstore(
        self,
        provider: VectorStoreProvider,
        collection_name: str,
        embeddings,
        documents: Optional[List[Any]] = None,
        persist_directory: Optional[str] = None,
        **kwargs
    ):
        """
        Create or load a vector store.
        
        Args:
            provider: Which vector store to use
            collection_name: Name of the collection/index
            embeddings: Embeddings instance from EmbeddingManager
            documents: Optional list of documents to add immediately
            persist_directory: Where to store data (for persistent stores)
            **kwargs: Provider-specific options
            
        Returns:
            LangChain VectorStore instance
        """
        cache_key = f"{provider}:{collection_name}"
        
        # Return cached instance if available and no new documents
        if cache_key in self._vectorstores_cache and not documents:
            logger.debug(f"Using cached vectorstore: {cache_key}")
            return self._vectorstores_cache[cache_key]
        
        # Create new vector store
        vectorstore = self._create_vectorstore(
            provider, collection_name, embeddings, documents, persist_directory, **kwargs
        )
        
        # Cache it
        self._vectorstores_cache[cache_key] = vectorstore
        logger.info(f"✅ Created vectorstore: {cache_key}")
        
        return vectorstore
    
    def _create_vectorstore(
        self,
        provider: VectorStoreProvider,
        collection_name: str,
        embeddings,
        documents: Optional[List[Any]],
        persist_directory: Optional[str],
        **kwargs
    ):
        """Create vector store based on provider."""
        
        if provider == VectorStoreProvider.CHROMA:
            return self._create_chroma(collection_name, embeddings, documents, persist_directory, **kwargs)
        
        elif provider == VectorStoreProvider.FAISS:
            return self._create_faiss(embeddings, documents, **kwargs)
        
        elif provider == VectorStoreProvider.PINECONE:
            return self._create_pinecone(collection_name, embeddings, documents, **kwargs)
        
        elif provider == VectorStoreProvider.WEAVIATE:
            return self._create_weaviate(collection_name, embeddings, documents, **kwargs)
        
        else:
            raise ValueError(f"Unknown vector store provider: {provider}")
    
    def _create_chroma(
        self,
        collection_name: str,
        embeddings,
        documents: Optional[List[Any]],
        persist_directory: Optional[str],
        **kwargs
    ):
        """
        Create Chroma vector store (FREE, local, persistent).
        
        Perfect for:
        - Local development
        - Small to medium datasets
        - Cost-conscious deployments
        """
        try:
            from langchain_community.vectorstores import Chroma
        except ImportError:
            raise ImportError("Chroma requires: pip install chromadb")
        
        persist_dir = persist_directory or str(self.default_persist_dir / collection_name)
        
        logger.info(f"🏠 Creating Chroma vectorstore: {collection_name} (persist: {persist_dir})")
        
        if documents:
            return Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                collection_name=collection_name,
                persist_directory=persist_dir,
                **kwargs
            )
        else:
            return Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=persist_dir,
                **kwargs
            )
    
    def _create_faiss(
        self,
        embeddings,
        documents: Optional[List[Any]],
        **kwargs
    ):
        """
        Create FAISS vector store (FREE, local, in-memory, VERY FAST).
        
        Perfect for:
        - High-performance search
        - Large datasets that fit in RAM
        - Research and experimentation
        
        Note: Not persistent by default (use save_local/load_local)
        """
        try:
            from langchain_community.vectorstores import FAISS
        except ImportError:
            raise ImportError("FAISS requires: pip install faiss-cpu")
        
        logger.info(f"🏠 Creating FAISS vectorstore (in-memory)")
        
        if not documents:
            raise ValueError("FAISS requires documents to initialize")
        
        return FAISS.from_documents(
            documents=documents,
            embedding=embeddings,
            **kwargs
        )
    
    def _create_pinecone(
        self,
        collection_name: str,
        embeddings,
        documents: Optional[List[Any]],
        **kwargs
    ):
        """
        Create Pinecone vector store (PAID, cloud, scalable).
        
        Perfect for:
        - Production deployments
        - Large-scale applications
        - Multi-region availability
        """
        try:
            from langchain_community.vectorstores import Pinecone
            import pinecone
        except ImportError:
            raise ImportError("Pinecone requires: pip install pinecone-client")
        
        logger.info(f"☁️ Creating Pinecone vectorstore: {collection_name}")
        
        # Note: Pinecone requires initialization with API key
        # Users should set PINECONE_API_KEY and PINECONE_ENVIRONMENT in env
        
        if documents:
            return Pinecone.from_documents(
                documents=documents,
                embedding=embeddings,
                index_name=collection_name,
                **kwargs
            )
        else:
            return Pinecone.from_existing_index(
                index_name=collection_name,
                embedding=embeddings,
                **kwargs
            )
    
    def _create_weaviate(
        self,
        collection_name: str,
        embeddings,
        documents: Optional[List[Any]],
        **kwargs
    ):
        """Create Weaviate vector store (PAID/FREE, cloud/local)."""
        try:
            from langchain_community.vectorstores import Weaviate
            import weaviate
        except ImportError:
            raise ImportError("Weaviate requires: pip install weaviate-client")
        
        logger.info(f"☁️ Creating Weaviate vectorstore: {collection_name}")
        
        # Note: Weaviate requires a client connection
        # Users should configure Weaviate URL and auth in env
        
        raise NotImplementedError("Weaviate integration coming soon!")
    
    def similarity_search(
        self,
        vectorstore,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Any]:
        """
        Perform similarity search on a vector store.
        
        Args:
            vectorstore: Vector store instance
            query: Search query
            k: Number of results to return
            **kwargs: Provider-specific options
            
        Returns:
            List of similar documents
        """
        logger.debug(f"🔍 Similarity search: '{query[:50]}...' (k={k})")
        return vectorstore.similarity_search(query, k=k, **kwargs)
    
    def add_documents(
        self,
        vectorstore,
        documents: List[Any]
    ):
        """
        Add documents to an existing vector store.
        
        Args:
            vectorstore: Vector store instance
            documents: Documents to add
        """
        logger.info(f"➕ Adding {len(documents)} documents to vectorstore")
        vectorstore.add_documents(documents)

