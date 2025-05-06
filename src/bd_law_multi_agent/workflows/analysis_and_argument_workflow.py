from bd_law_multi_agent.core.common import logger
from bd_law_multi_agent.core.config import config
from langchain.callbacks.manager import tracing_v2_enabled
from langgraph.graph import StateGraph, END
import logging
from bd_law_multi_agent.schemas.agent_state_sc import AgentState
from bd_law_multi_agent.services.legal_service import LegalAnalyzer
from bd_law_multi_agent.services.rag_service import PersistentLegalRAG
from bd_law_multi_agent.prompts.case_analysis_prompt import CASE_ANALYSIS_PROMPT






# Initialize RAG system
rag_system = PersistentLegalRAG()

# Node Definitions returning state updates
def retrieve_documents(state: AgentState):
    logger.info("Retrieving relevant documents...")
    documents = rag_system.vector_store.similarity_search(
        state["query"], 
        k=config.MAX_RETRIEVED_DOCS
    )
    return {"documents": documents, "current_step": "retrieved_docs"}

def classify_case(state: AgentState):
    logger.info("Classifying case...")
    context = "\n".join([doc.page_content for doc in state["documents"]])
    classification = LegalAnalyzer.classify_case(
        state["query"], 
        context=context
    )
    return {"classification": classification, "current_step": "classified_case"}

def generate_analysis(state: AgentState):
    logger.info("Generating legal analysis...")
    context = "\n\n".join([
        f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content[:500]}"
        for doc in state["documents"]
    ])
    
    prompt = CASE_ANALYSIS_PROMPT.get_legal_analysis_prompt().format(
        classification_context=(
            f"Category: {state['classification'].get('primary_category', 'N/A')}\n"
            f"Complexity: {state['classification'].get('complexity_level', 'N/A')}"
        ),
        context=context,
        query=state["query"]
    )
    
    analysis = rag_system.llm.invoke(prompt).content
    return {"analysis": analysis, "current_step": "generated_analysis"}


def generate_follow_ups(state: AgentState):
    logger.info("Generating follow-up questions...")
    # Convert the conversation history to the format expected by LegalAnalyzer
    history_for_followups = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": msg} 
        for i, msg in enumerate(state["conversation_history"])
    ] if state["conversation_history"] else []
    
    follow_ups = LegalAnalyzer.generate_follow_up_questions(
        state["analysis"],
        history_for_followups
    )
    return {"follow_ups": follow_ups, "current_step": "generated_follow_ups"}


def generate_legal_argument(state: AgentState):
    """New argument generation node"""
    logger.info("Generating legal argument...")
    try:
        case_details = state["analysis"]  # Use analysis as case details
        classification = state["classification"]
       
        # Retrieve legislation-specific documents
        docs = rag_system.vector_store.similarity_search(
            case_details,
            k=config.MAX_RETRIEVED_DOCS,
            filter={"document_type": "Legislation"},
            similarity_threshold=0.75
        )
        
        # Store documents in state for later use
        state["documents"] = docs
       
        # Build legal context
        context = "\n\n".join([
            f"Source: {doc.metadata['source']}\nContent:{doc.page_content[:config.CITATION_LENGTH]}"
            for doc in docs
        ])
       
        # Generate the argument
        argument = LegalAnalyzer.generate_legal_argument(
            case_details=case_details,
            context=context,
            category=classification["primary_category"]
        )
       
        # Create a properly structured return that includes both updates to state
        # and maintains the existing state values
        return {
            **state,  # Preserve existing state
            "argument": argument,  
            "legal_category": classification["primary_category"],
            "current_step": "generated_argument"
        }
    except Exception as e:
        logger.error(f"Argument generation failed: {e}")
        return {**state, "argument": "", "error": str(e)}




def update_history(state: AgentState):
    logger.info("Updating conversation history...")
    # Get the appropriate response content
    response_content = state.get("analysis", state.get("argument", ""))
    
    new_history = state["conversation_history"] + [
        state["query"],
        response_content  # Use either analysis or argument
    ]
    return {"conversation_history": new_history, "current_step": "updated_history"}

# Conditional Edge Logic
def should_continue(state: AgentState):
    if "follow_up" in state["query"].lower():
        return "continue_analysis"
    return "end"





def create_legal_workflow():
    """Updated workflow without argument generation"""
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("retrieve", retrieve_documents)
    workflow.add_node("classify", classify_case)
    workflow.add_node("analyze", generate_analysis)
    workflow.add_node("followups", generate_follow_ups)
    workflow.add_node("update_history", update_history)
    
    # Set Entry Point
    workflow.set_entry_point("retrieve")
    
    # Add Edges
    workflow.add_edge("retrieve", "classify")
    workflow.add_edge("classify", "analyze")
    workflow.add_edge("analyze", "followups")  
    workflow.add_edge("followups", "update_history")
    
    # Conditional Edge
    workflow.add_conditional_edges(
        "update_history",
        should_continue,
        {"continue_analysis": "retrieve", "end": END}
    )
    
    
    workflow.add_conditional_edges(
        "retrieve",
        lambda s: "end" if s.get("error") else "classify"
    )
    
    return workflow.compile()





def create_argument_workflow():
    """Updated workflow with argument generation"""
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("retrieve", retrieve_documents)
    workflow.add_node("classify", classify_case)
    workflow.add_node('argument_generate', generate_legal_argument)
    workflow.add_node("update_history", update_history)
    
    # Set Entry Point
    workflow.set_entry_point("retrieve")
    
    # Add Edges
    workflow.add_edge("retrieve", "classify")
    workflow.add_edge("classify", "argument_generate")
    workflow.add_edge("argument_generate", "update_history")
    
  
    
    # Conditional Edge
    workflow.add_conditional_edges(
        "update_history",
        should_continue,
        {"continue_analysis": "retrieve", "end": END}
    )
    
    workflow.add_conditional_edges(
        "retrieve",
        lambda s: "end" if s.get("error") else "classify"
    )
    
    return workflow.compile()

argument_agent = create_argument_workflow()
legal_agent = create_legal_workflow()










