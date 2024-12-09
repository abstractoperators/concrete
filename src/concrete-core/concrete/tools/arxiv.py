from concrete.tools.meta import MetaTool

try:
    import arxiv
except ImportError as e:
    raise ImportError("Failed to import arxiv: " + str(e) + "\nInstall concrete[tool-arxiv] to use ArxivTool")


class ArxivTool(metaclass=MetaTool):
    client: arxiv.Client = arxiv.Client()

    @classmethod
    def _search(
        cls,
        query: str,
        id_list: list[str],
        max_results: int,
        sort_by: str,
        sort_order: str,
    ) -> list[arxiv.Result]:
        """
        Helper function to search and return a list of arXiv articles.
        Uses only simple types available to OpenAI Structured Output
        """
        search: arxiv.Search = arxiv.Search(
            query=query,
            id_list=id_list,
            max_results=max_results,
            sort_by=getattr(arxiv.SortCriterion, sort_by),
            sort_order=getattr(arxiv.SortOrder, sort_order),
        )

        results: list[arxiv.Result] = list(cls.client.results(search))

        return results

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
