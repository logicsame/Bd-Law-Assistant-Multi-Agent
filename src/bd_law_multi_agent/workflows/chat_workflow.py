from bd_law_multi_agent.core.config import config
from langgraph.graph import StateGraph, END
from bd_law_multi_agent.core.common import logger
from typing import Dict, List, Any, Optional, TypedDict
from bd_law_multi_agent.services.rag_service import PersistentLegalRAG
from bd_law_multi_agent.prompts.lega_chat_prompy import LegalChatbotPrompts
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq



rag_system = PersistentLegalRAG()

class ChatState(TypedDict, total=False):
    """Type for chat agent state"""
    query: str
    documents: List[Any]
    response: str
    response_type: str
    sources: List[Dict[str, str]]
    conversation_history: List[Dict[str, str]]
    current_step: str
    doc_type: str
    query_type: str
    error: Optional[str]

# Node Definitions returning state updates
def retrieve_chat_context(state: ChatState) -> ChatState:
    """Retrieve relevant documents for the chat query"""
    logger.info("Retrieving context for chat query...")
    
    # Get doc type based on query content
    doc_type = "General"
    query = state["query"]
    
    if any(term in query.lower() for term in ["define", "what is", "meaning of"]):
        doc_type = "Dictionary"
    elif any(term in query.lower() for term in ["case law", "precedent"]):
        doc_type = "CaseLaw"  
    elif any(term in query.lower() for term in ["section", "article"]):
        doc_type = "Legislation"
    
    try:
        # Retrieve relevant documents
        documents = rag_system.vector_store.similarity_search(
            query, 
            k=config.MAX_RETRIEVED_DOCS,
            filter={"document_type": doc_type} if doc_type != "General" else None,
            similarity_threshold=0.65
        )
        
        # Return updated state
        return {
            "documents": documents, 
            "current_step": "retrieved_context", 
            "doc_type": doc_type
        }
    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        return {
            "documents": [],
            "current_step": "error",
            "error": str(e)
        }

def determine_query_type(state: ChatState) -> ChatState:
    """Determine the type of query to route appropriately"""
    logger.info("Determining query type...")
    query = state["query"].lower()
    
    if any(keyword in query for keyword in ["define", "what is", "meaning of"]):
        query_type = "definition"
    elif any(keyword in query for keyword in ["analyze", "explain", "implications of"]):
        query_type = "analysis"
    else:
        query_type = "general_advice"
        
    return {"query_type": query_type, "current_step": "determined_query_type"}

def generate_definition_response(state: ChatState) -> ChatState:
    """Generate response for definition queries"""
    logger.info("Generating definition response...")
    term = state["query"].replace("define", "").replace("what is", "").replace("meaning of", "").strip()
    
    context = "\n\n".join([
        f"Source: {doc.metadata.get('source', 'Unknown')}\n"
        f"Content:\n{doc.page_content}"
        for doc in state["documents"]
    ])
    
    prompt = LegalChatbotPrompts.get_definition_prompt(term, context)
    # llm = ChatOpenAI(
    #     model=config.LLM_MODEL,
    #     temperature=config.TEMPERATURE,
    #     max_tokens=config.MAX_TOKENS
    # )
    llm = ChatGroq(
        model = config.GROQ_LLM_MODEL,
        temperature=config.TEMPERATURE
    )
    
    response = llm.invoke(prompt).content
    
    return {
        "response": response, 
        "response_type": "definition",
        "current_step": "generated_response"
    }

def generate_analysis_response(state: ChatState) -> ChatState:
    """Generate response for analysis queries"""
    logger.info("Generating analysis response...")
    term = state["query"].replace("analyze", "").replace("explain", "").replace("implications of", "").strip()
    
    context = "\n\n".join([
        f"Source: {doc.metadata.get('source', 'Unknown')}\n"
        f"Content:\n{doc.page_content}"
        for doc in state["documents"]
    ])
    
    prompt = LegalChatbotPrompts.get_term_analysis_prompt(term, context)
    # llm = ChatOpenAI(
    #     model=config.LLM_MODEL,
    #     temperature=config.TEMPERATURE,
    #     max_tokens=config.MAX_TOKENS
    # )
    llm = ChatGroq(
        model=config.GROQ_LLM_MODEL,
        temperature=config.TEMPERATURE,
    )
    response = llm.invoke(prompt).content
    
    return {
        "response": response, 
        "response_type": "analysis",
        "current_step": "generated_response"
    }

def generate_general_response(state: ChatState) -> ChatState:
    """Generate response for general queries"""
    logger.info("Generating general advice response...")
    query = state["query"]
    
    context = "\n\n".join([
        f"Source: {doc.metadata.get('source', 'Unknown')}\n"
        f"Content:\n{doc.page_content}"
        for doc in state["documents"]
    ])
    
    prompt = LegalChatbotPrompts.get_general_advice_prompt(query, context)
    # llm = ChatOpenAI(
    #     model=config.LLM_MODEL,
    #     temperature=config.TEMPERATURE,
    #     max_tokens=config.MAX_TOKENS
    # )
    
    llm = ChatGroq(
        model = config.GROQ_LLM_MODEL,
        temperature=config.TEMPERATURE
    )
    
    response = llm.invoke(prompt).content
    
    return {
        "response": response, 
        "response_type": "general_advice",
        "current_step": "generated_response"
    }

def extract_sources(state: ChatState) -> ChatState:
    """Extract and format sources from documents"""
    logger.info("Extracting sources...")
    
    sources = []
    for doc in state["documents"]:
        source = doc.metadata.get("source_path", "Unknown")
        excerpt = doc.page_content
        
        sources.append({
            "source": source,
            "excerpt": excerpt[:200] + "..." if len(excerpt) > 200 else excerpt,
        })
    
    return {"sources": sources, "current_step": "extracted_sources"}

def update_chat_history(state: ChatState) -> ChatState:
    """Update the conversation history with the new exchange"""
    logger.info("Updating chat history...")
    
    history = state.get("conversation_history", [])
    new_history = history + [
        {"role": "user", "content": state["query"]},
        {"role": "assistant", "content": state["response"]}
    ]
    
    return {"conversation_history": new_history, "current_step": "completed"}

# Conditional Edge Logic
def route_by_query_type(state: ChatState) -> str:
    """Route to the appropriate response generator based on query type"""
    query_type = state.get("query_type", "general_advice")
    
    if query_type == "definition":
        return "definition"
    elif query_type == "analysis":
        return "analysis"
    else:
        return "general_advice"

def should_continue_chat(state: ChatState) -> str:
    """Determine if the conversation should continue or end"""
    # Always end for now, can be enhanced later
    return "end"

def check_for_errors(state: ChatState) -> str:
    """Check if there were errors in retrieval"""
    if "error" in state and state["error"]:
        return "end"
    return "continue"

def create_chat_workflow():
    """Create a LangGraph workflow for the chat system"""
    # Use proper type annotation for graph
    workflow = StateGraph(ChatState)
    
    # Add Nodes
    workflow.add_node("retrieve", retrieve_chat_context)
    workflow.add_node("determine_type", determine_query_type)
    workflow.add_node("definition_response", generate_definition_response)
    workflow.add_node("analysis_response", generate_analysis_response)
    workflow.add_node("general_response", generate_general_response)
    workflow.add_node("extract_sources", extract_sources)
    workflow.add_node("update_history", update_chat_history)
    
    # Set Entry Point
    workflow.set_entry_point("retrieve")
    
    # Add Conditional Edges for error handling
    workflow.add_conditional_edges(
        "retrieve",
        check_for_errors,
        {
            "continue": "determine_type",
            "end": END
        }
    )
    
    # Add Conditional Edges for query type routing
    workflow.add_conditional_edges(
        "determine_type",
        route_by_query_type,
        {
            "definition": "definition_response",
            "analysis": "analysis_response",
            "general_advice": "general_response"
        }
    )
    
    # Merge the response paths
    workflow.add_edge("definition_response", "extract_sources")
    workflow.add_edge("analysis_response", "extract_sources")
    workflow.add_edge("general_response", "extract_sources")
    workflow.add_edge("extract_sources", "update_history")
    
    # Add conditional edge to either continue or end
    workflow.add_conditional_edges(
        "update_history",
        should_continue_chat,
        {"continue": "retrieve", "end": END}
    )
    
    return workflow.compile()

# Create the chat agent
chat_agent = create_chat_workflow()