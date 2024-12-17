try:
    from llama_index.core import StorageContext, VectorStoreIndex
    from llama_index.core.base.base_retriever import BaseRetriever
    from llama_index.core.schema import Document
    from llama_index.vector_stores.postgres import PGVectorStore
except ImportError as e:
    raise ImportError("Install concrete[document-retriever] to use document retrieval (aka 'rag') functionality") from e

import os

from concrete.tools import MetaTool


class DocumentTool(metaclass=MetaTool):
    """
    This is a tool for retrieving and inserting documents from a document store.
    Contains a pre-configured document store found in the environment variables.
    """

    drivername: str = os.environ.get("POSTGRES_VECTOR_DB_DRIVER", "")
    username: str = os.environ.get("POSTGRES_VECTOR_DB_USERNAME", "")
    password: str = os.environ.get("POSTGRES_VECTOR_DB_PASSWORD", "")
    host: str = os.environ.get("POSTGRES_VECTOR_DB_HOST", "")
    port: int = int(os.environ.get("POSTGRES_VECTOR_DB_PORT") or "0")
    database: str = os.environ.get("POSTGRES_VECTOR_DB_DATABASE", "")
    vector_store_table: str = os.environ.get("POSTGRES_VECTOR_STORE_TABLE", "")

    if not all([drivername, username, password, host, port, database, vector_store_table]):
        raise ValueError("Missing environment variables for database connection.")

    # Don't use sqlalchemy.url to limit deps
    url: str = f"{drivername}://{username}:{password}@{host}:{port}/{database}"
    # Not used, but required for instantiation of vector_store
    async_url: str = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"

    connect_args: dict = {"sslmode": 'require', "sslrootcert": "../us-east-1-bundle.pem"}
    vector_store: PGVectorStore = PGVectorStore.from_params(
        connection_string=url,
        async_connection_string=async_url,  # Required for vector store creation
        table_name=vector_store_table,
        embed_dim=1536,
        hnsw_kwargs={
            "hnsw_m": 16,
            "hnsw_ef_construction": 64,
            "hnsw_ef_search": 40,
            "hnsw_dist_method": "vector_cosine_ops",
        },
        hybrid_search=True,
        text_search_config="english",
        create_engine_kwargs={"connect_args": connect_args},
    )

    storage_context: StorageContext = StorageContext.from_defaults(
        vector_store=vector_store,
    )

    index: VectorStoreIndex = VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context,
        use_async=False,
    )

    retriever: BaseRetriever = index.as_retriever(similarity_top_k=2)

    @classmethod
    def retrieve_document(cls, query: str) -> str:
        """
        Provides an interface for retrieving documents from a pre-configured document store.

        Args:
            query (str): The query string to search for
        Returns:
            A list of retrieved documents formatted as a string.
            The document retrieved from the document store
        """

        res: list[str] = []
        nodes = cls.retriever.retrieve(query)
        for i, node in enumerate(nodes):
            res.append(f'Retrieved Document {i + 1}: \n{node.get_content()}')

        return "\n\n".join(res)

    @classmethod
    def insert_text_as_document(cls, text: str) -> None:
        """
        Inserts text as a document into the document store.

        Args:
            document (str): The document to insert
        """

        cls.index.insert(Document(text=text))

    @classmethod
    def _insert_document(cls, document: Document) -> None:
        """
        Inserts a document into the document store.
        Note: LLMs can't use this yet because they don't have a way to make a Document object.


        Args:
            document (Document): The document to insert
        """

        cls.index.insert(document)
