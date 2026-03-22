"""
LangGraph agent that orchestrates RAG, Draft, and Review tools.

Graph structure:
  START → reasoning_node → [tool_node | END]
                ↑                |
                └────────────────┘
"""

from dataclasses import dataclass

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain.agents import create_agent
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.retry import async_llm_retry

from app.core.logging import get_logger
from app.services.draft_service import DraftService
from app.services.rag_service import RAGService
from app.services.review_service import ReviewService

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are a Bayer consumer health assistant. "
    "You have three tools available:\n"
    "- rag_tool: answer factual questions using the product/policy knowledge base\n"
    "- draft_tool: generate compliant marketing copy from a brief\n"
    "- review_tool: check whether marketing text is policy-compliant\n\n"
    "Choose the most appropriate tool based on the user's request. "
    "Always ground your final response in the tool output."
)


@dataclass
class AgentResult:
    answer: str
    tool_calls: list[str]
    citations: list[str]


class BayerAgent:
    def __init__(self, graph, pool: AsyncConnectionPool):
        self._graph = graph
        self._pool = pool

    @classmethod
    async def create(
        cls,
        rag_service: RAGService,
        draft_service: DraftService,
        review_service: ReviewService,
        openai_api_key: str,
        chat_model: str,
        database_url: str,
    ) -> "BayerAgent":
        def rag_tool(question: str) -> str:
            """Answer factual questions about Bayer products or policies using the knowledge base."""
            result = rag_service.answer(question)
            citations = ", ".join(result.citations) if result.citations else "none"
            return f"{result.answer}\n\nSources: {citations}"

        def draft_tool(brief: str) -> str:
            """Generate compliant marketing copy from a creative brief."""
            result = draft_service.draft(brief)
            citations = ", ".join(result.citations) if result.citations else "none"
            return f"{result.draft}\n\nSources: {citations}"

        def review_tool(marketing_text: str) -> str:
            """Review marketing text for regulatory compliance. Returns verdict and notes."""
            result = review_service.review(marketing_text)
            verdict = "COMPLIANT" if result.is_compliant else "NON-COMPLIANT"
            notes = "\n".join(f"- {n}" for n in result.notes)
            citations = ", ".join(result.citations) if result.citations else "none"
            return f"VERDICT: {verdict}\nNOTES:\n{notes}\n\nSources: {citations}"

        tools = [rag_tool, draft_tool, review_tool]
        llm = ChatOpenAI(model=chat_model, api_key=openai_api_key, temperature=0)

        # psycopg DSN (strip SQLAlchemy driver prefix used by asyncpg)
        pg_dsn = database_url.replace("postgresql+asyncpg://", "postgresql://")
        pool = AsyncConnectionPool(
            conninfo=pg_dsn,
            open=False,
            kwargs={"autocommit": True, "row_factory": dict_row},
        )
        await pool.open()

        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()  # creates langgraph checkpoint tables if absent

        graph = create_agent(
            llm,
            tools=tools,
            system_prompt=_SYSTEM_PROMPT,
            checkpointer=checkpointer,
        )

        logger.info("Bayer LangGraph agent initialised with Postgres checkpointer")
        return cls(graph=graph, pool=pool)

    async def close(self) -> None:
        """Close the Postgres connection pool on application shutdown."""
        await self._pool.close()

    async def run(
        self, query: str, thread_id: str = "default", request_id: str = "unknown"
    ) -> AgentResult:
        config = {
            "configurable": {"thread_id": thread_id},
            "tags": ["bayer-agent"],
            "metadata": {"thread_id": thread_id, "request_id": request_id},
        }
        async for attempt in async_llm_retry():
            with attempt:
                result = await self._graph.ainvoke(
                    {"messages": [HumanMessage(content=query)]},
                    config=config,
                )

        messages = result["messages"]
        final_answer = messages[-1].content

        tool_calls = [
            msg.name
            for msg in messages
            if hasattr(msg, "name") and msg.name is not None
        ]

        citations: list[str] = []
        for msg in messages:
            if isinstance(msg, ToolMessage) and isinstance(msg.content, str):
                for line in msg.content.splitlines():
                    if line.startswith("Sources:"):
                        sources = line.removeprefix("Sources:").strip()
                        if sources and sources != "none":
                            citations.extend(
                                s.strip() for s in sources.split(",") if s.strip()
                            )
        citations = list(dict.fromkeys(citations))  # deduplicate, preserve order

        logger.info(
            "Agent run complete",
            extra={"thread_id": thread_id, "tools_used": tool_calls},
        )
        return AgentResult(
            answer=final_answer, tool_calls=tool_calls, citations=citations
        )
