try:
    import llama_index
    import sqlalchemy
    from llama_index.core import StorageContext, VectorStoreIndex
    from llama_index.vector_stores.postgres import PGVectorStore
except ImportError as e:
    raise "Install concrete[document-retriever] to use document retrieval (aka 'rag') functionality" from e

import os

from concrete.tools import MetaTool


class DocumentRetriever(metaclass=MetaTool):
    """
    This is a tool for retrieving documents from a document store based on a query.
    """

    drivername = os.environ.get("DB_DRIVER")
    username = os.environ.get("DB_USERNAME")
    password = os.environ.get("DB_PASSWORD")
    host = os.environ.get("DB_HOST")
    port = int(os.environ.get("DB_PORT") or "0")
    database = os.environ.get("DB_DATABASE")

    # Don't use sqlalchemy.url to limit deps
    url = f"{drivername}://{username}:{password}@{host}:{port}/{database}"

    connect_args = {"sslmode": 'require', "sslrootcert": "../us-east-1-bundle.pem"}

    vector_store_table = os.environ.get("VECTOR_STORE_TABLE")

    vector_store = PGVectorStore.from_params(
        connection_string=url,
        async_connection_string=url,  # Required and unused
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

    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
    retriever = index.as_retriever(
        similarity_top_k=2
    )  # Not clear the difference between a retriever and a query engine

    @classmethod
    def retrieve_document(cls, query: str) -> str:
        """
        Provides an interface for retrieving documents from a pre-configured document store.

        query (str): The query string to search for

        returns (str): The document retrieved from the document store
        """

        return cls.retriever.retrieve(query)
        # Probably have class vars for the llama index document store
