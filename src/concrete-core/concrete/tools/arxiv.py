from concrete.tools.meta import MetaTool

try:
    import arxiv

    # import pymupdf
    import pymupdf4llm
    from llama_index.core.schema import Document
except ImportError as e:
    raise ImportError(
        "Failed optional imports for tool-arxiv. Please install concrete[tool-arxiv] to continue. "
    ) from e


class ArxivTool(metaclass=MetaTool):
    client: arxiv.Client = arxiv.Client()

    @classmethod
    def _search(
        cls,
        query: str = "",
        id_list: list[str] = [],
        max_results: int | None = None,
        sort_by: str = "Relevance",
        sort_order: str = "Descending",
    ) -> list[arxiv.Result]:
        """
        Helper function to search and return a list of arXiv articles.
        Uses only simple types available to OpenAI Structured Output
        """
        if not query and not id_list:
            raise ValueError("At least one of query or id_list must be provided.")

        search: arxiv.Search = arxiv.Search(
            query=query,
            id_list=id_list,
            max_results=max_results,
            sort_by=getattr(arxiv.SortCriterion, sort_by),
            sort_order=getattr(arxiv.SortOrder, sort_order),
        )

        results: list[arxiv.Result] = list(cls.client.results(search))

        return results

    @classmethod
    def search(
        cls,
        query: str,
        id_list: list[str] = [],
        max_results: int = 10,
        sort_by: str = "Relevance",
        sort_order: str = "Descending",
    ) -> str:
        """
        Search and return a list of arXiv articles.

        query (str): The query string to search for
        id_list (list[str] | None): A list of arXiv article IDs to which to limit the search. If no list is provided, all articles are searched.
        max_results (int): The maximum number of results to return. Limit is 300_000
        sort_by (str): The name of the SortCriterion to sort by.
            Options include: Relevance, LastUpdatedDate, SubmittedDate
        sort_order (str): The order in which to sort the results.
            Options include: Ascending, Descending
        """  # noqa

        results: list[arxiv.Result] = cls._search(
            query=query,
            id_list=id_list,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return "\n\n".join([repr(result) for result in results])

    @classmethod
    def _download_paper_pdf(cls, id: str) -> None:
        """
        Downloads the PDF of an arXiv paper.

        Args:
            id (str): Paper ID to get the full text of (e.g. "1605.08386v1")
        Returns:
            None
        """
        paper: arxiv.Result = cls._search(id_list=[id])[0]
        paper.download_pdf(filename=f'{id}.pdf')

    @classmethod
    def get_arxiv_paper_as_llama_document(cls, id: str) -> list[Document]:
        """
        Downloads the PDF of an arXiv paper. Parses and returns the paper as a list of LlamaDocuments.

        Args:
            id (str): Paper ID to get the full text of (e.g. "1605.08386v1")
        Returns:
            list[Document]: List of LlamaDocuments representing the paper
        """
        llama_reader = pymupdf4llm.LlamaMarkdownReader()
        cls._download_paper_pdf(id)
        llama_doc = llama_reader.load_data(f'{id}.pdf')
        return llama_doc
