import logging
from langgraph.graph import StateGraph ,START , END 
from langgraph.checkpoint.postgres import PostgresSaver 
from langchain_core.messages import HumanMessage,AIMessage


from src.agent.state import AgentState
from src.database.vector_store import VectorStore
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.reranker import Reranker
from src.ingestion.embedder import EmbeddingService
from src.resilience.llm_fallback_manager import LLMFallbackManager, build_default_llm_manager
from src.config.settings import settings

logger = logging.getLogger(__name__)


def make_route_node(llm:LLMFallbackManager):
    def route_question(state:AgentState)-> dict:
        prompt=(  "Classify this question as either 'retrieve' (needs looking up "
            "information from documents) or 'direct' (a greeting, small talk, "
            "or something answerable without any document lookup). "
            "Respond with ONLY the single word 'retrieve' or 'direct'.\n\n"
            f"Question: {state['questions']}"
            
            )
        
        try:
            decision = llm.generate(prompt,max_tokens=10).strip().lower()
            
            route = "retrieve" if "retrieve" in decision else "direct"
        
        
        except Exception as e :
            logger.warning(f"route failed defaltuing to retrieve {e}")
            route = "retrieve"
            
        return {"route":route}
    return route_question




def make_retrieve_node(retriever:HybridRetriever,reranker:Reranker):
    def retrieve(state:AgentState)->dict:
        from uuid import UUID
        query = state.get("rewritten_questions") or state["questions"]
        results = retriever.retrieve_with_parents(
            query_text=query,
            tenant_id=UUID(state["tenant_id"]),
            k=10
        )
        
        reranked = reranker.rerank(query,results,top_n=5)
        return {"documents":reranked}
    return retrieve

def make_generate_node(llm:LLMFallbackManager):
    def generate_answer(state:AgentState)->dict:
        
        
        documents=state.get("documents",[])
            
        if documents:
            
            context = "\n\n---\n\n".join(
            d.get("generation_content", d.get("content", "")) for d in documents)
            prompt = (
            "Answer the question using ONLY the information in the context below. "
            "If the context doesn't contain enough information to answer, say so honestly.\n\n"
            f"<retrieved_context>\n{context}\n</retrieved_context>\n\n"
            f"Question: {state['questions']}\n\nAnswer:")

        else:
            
            prompt=f"Answer this question directly and concisely: {state['questions']}"
            
        answer = llm.generate(prompt,max_tokens=500)
            
        return { "generation": answer,
            "messages": [AIMessage(content=answer)],}
    
    
    return generate_answer
        
        
#  =============================================
#  Graph builder 
# ===========================================


def build_graph(checkpointer:None):
    llm=build_default_llm_manager()
    embedding_service = EmbeddingService()
    vector_store = VectorStore()
    retriever = HybridRetriever(embedding_service, vector_store)
    reranker = Reranker()
    
    graph = StateGraph(AgentState)
    
    graph.add_node("route",make_route_node(llm))
    graph.add_node("retrieve",make_retrieve_node(retriever=retriever,reranker=reranker))
    graph.add_node("generate",make_generate_node(llm))
    
    graph.add_edge(START,"route")
    
    graph.add_conditional_edges(
        "route",
        lambda state: state["route"],
        {"retrieve": "retrieve", "direct": "generate"},
    )
    
    graph.add_edge("retrieve","generate")
    graph.add_edge("generate",END)
    
    return graph.compile(checkpointer=checkpointer)


from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver

def build_checkpointer():
    """
    Postgres-backed checkpointer — this is what gives you real
    short-term memory across turns, keyed by conversation_id (LangGraph
    calls this a 'thread_id'). Persists to your same Supabase Postgres
    instance via connection pool (survives idle disconnects, unlike a
    single raw connection).
    """
    conn_string = settings.SUPABASE_DB_CONNECTION_STRING

    pool = ConnectionPool(
        conninfo=conn_string,
        max_size=10,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=True,  # opens the pool immediately
    )

    checkpointer = PostgresSaver(pool)
    checkpointer.setup()  # creates the checkpoint tables if they don't exist yet
    return checkpointer

    
    

        
    