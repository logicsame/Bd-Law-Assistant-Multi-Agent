# from bd_law_multi_agent.core.common import logger
# from bd_law_multi_agent.core.config import config
# from langchain.callbacks.manager import tracing_v2_enabled
# from langgraph.graph import StateGraph, END
# import logging
# from bd_law_multi_agent.schemas.agent_state_sc import AgentState
# from bd_law_multi_agent.services.legal_service import LegalAnalyzer
# from bd_law_multi_agent.services.rag_service import PersistentLegalRAG
# from bd_law_multi_agent.prompts.case_analysis_prompt import CASE_ANALYSIS_PROMPT






# # Initialize RAG system
# rag_system = PersistentLegalRAG()

# # Node Definitions returning state updates
# def retrieve_documents(state: AgentState):
#     logger.info("Retrieving relevant documents...")
#     documents = rag_system.vector_store.similarity_search(
#         state["query"], 
#         k=config.MAX_RETRIEVED_DOCS
#     )
#     return {"documents": documents, "current_step": "retrieved_docs"}

# def classify_case(state: AgentState):
#     logger.info("Classifying case...")
#     context = "\n".join([doc.page_content for doc in state["documents"]])
#     classification = LegalAnalyzer.classify_case(
#         state["query"], 
#         context=context
#     )
#     return {"classification": classification, "current_step": "classified_case"}

# def generate_analysis(state: AgentState):
#     logger.info("Generating legal analysis...")
#     context = "\n\n".join([
#         f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content[:500]}"
#         for doc in state["documents"]
#     ])
    
#     prompt = CASE_ANALYSIS_PROMPT.get_legal_analysis_prompt().format(
#         classification_context=(
#             f"Category: {state['classification'].get('primary_category', 'N/A')}\n"
#             f"Complexity: {state['classification'].get('complexity_level', 'N/A')}"
#         ),
#         context=context,
#         query=state["query"]
#     )
    
#     analysis = rag_system.llm.invoke(prompt).content
#     return {"analysis": analysis, "current_step": "generated_analysis"}


# def generate_follow_ups(state: AgentState):
#     logger.info("Generating follow-up questions...")
#     # Convert the conversation history to the format expected by LegalAnalyzer
#     history_for_followups = [
#         {"role": "user" if i % 2 == 0 else "assistant", "content": msg} 
#         for i, msg in enumerate(state["conversation_history"])
#     ] if state["conversation_history"] else []
    
#     follow_ups = LegalAnalyzer.generate_follow_up_questions(
#         state["analysis"],
#         history_for_followups
#     )
#     return {"follow_ups": follow_ups, "current_step": "generated_follow_ups"}


# def generate_legal_argument(state: AgentState):
#     """New argument generation node"""
#     logger.info("Generating legal argument...")
#     try:
#         case_details = state["analysis"]  # Use analysis as case details
#         classification = state["classification"]
       
#         # Retrieve legislation-specific documents
#         docs = rag_system.vector_store.similarity_search(
#             case_details,
#             k=config.MAX_RETRIEVED_DOCS,
#             filter={"document_type": "Legislation"},
#             similarity_threshold=0.75
#         )
        
#         # Store documents in state for later use
#         state["documents"] = docs
       
#         # Build legal context
#         context = "\n\n".join([
#             f"Source: {doc.metadata['source']}\nContent:{doc.page_content[:config.CITATION_LENGTH]}"
#             for doc in docs
#         ])
       
#         # Generate the argument
#         argument = LegalAnalyzer.generate_legal_argument(
#             case_details=case_details,
#             context=context,
#             category=classification["primary_category"]
#         )
       
#         # Create a properly structured return that includes both updates to state
#         # and maintains the existing state values
#         return {
#             **state,  # Preserve existing state
#             "argument": argument,  
#             "legal_category": classification["primary_category"],
#             "current_step": "generated_argument"
#         }
#     except Exception as e:
#         logger.error(f"Argument generation failed: {e}")
#         return {**state, "argument": "", "error": str(e)}




# def update_history(state: AgentState):
#     logger.info("Updating conversation history...")
#     # Get the appropriate response content
#     response_content = state.get("analysis", state.get("argument", ""))
    
#     new_history = state["conversation_history"] + [
#         state["query"],
#         response_content  # Use either analysis or argument
#     ]
#     return {"conversation_history": new_history, "current_step": "updated_history"}

# # Conditional Edge Logic
# def should_continue(state: AgentState):
#     if "follow_up" in state["query"].lower():
#         return "continue_analysis"
#     return "end"





# def create_legal_workflow():
#     """Updated workflow without argument generation"""
#     workflow = StateGraph(AgentState)
    
#     # Add Nodes
#     workflow.add_node("retrieve", retrieve_documents)
#     workflow.add_node("classify", classify_case)
#     workflow.add_node("analyze", generate_analysis)
#     workflow.add_node("followups", generate_follow_ups)
#     workflow.add_node("update_history", update_history)
    
#     # Set Entry Point
#     workflow.set_entry_point("retrieve")
    
#     # Add Edges
#     workflow.add_edge("retrieve", "classify")
#     workflow.add_edge("classify", "analyze")
#     workflow.add_edge("analyze", "followups")  
#     workflow.add_edge("followups", "update_history")
    
#     # Conditional Edge
#     workflow.add_conditional_edges(
#         "update_history",
#         should_continue,
#         {"continue_analysis": "retrieve", "end": END}
#     )
    
    
#     workflow.add_conditional_edges(
#         "retrieve",
#         lambda s: "end" if s.get("error") else "classify"
#     )
    
#     return workflow.compile()





# def create_argument_workflow():
#     """Updated workflow with argument generation"""
#     workflow = StateGraph(AgentState)
    
#     # Add Nodes
#     workflow.add_node("retrieve", retrieve_documents)
#     workflow.add_node("classify", classify_case)
#     workflow.add_node('argument_generate', generate_legal_argument)
#     workflow.add_node("update_history", update_history)
    
#     # Set Entry Point
#     workflow.set_entry_point("retrieve")
    
#     # Add Edges
#     workflow.add_edge("retrieve", "classify")
#     workflow.add_edge("classify", "argument_generate")
#     workflow.add_edge("argument_generate", "update_history")
    
  
    
#     # Conditional Edge
#     workflow.add_conditional_edges(
#         "update_history",
#         should_continue,
#         {"continue_analysis": "retrieve", "end": END}
#     )
    
#     workflow.add_conditional_edges(
#         "retrieve",
#         lambda s: "end" if s.get("error") else "classify"
#     )
    
#     return workflow.compile()

# argument_agent = create_argument_workflow()
# legal_agent = create_legal_workflow()





from bd_law_multi_agent.utils.logger import logger

from bd_law_multi_agent.core.config import config
from langchain.callbacks.manager import tracing_v2_enabled
from langgraph.graph import StateGraph, END
import logging
from typing import Generator # Added for type hinting generators

from bd_law_multi_agent.schemas.agent_state_sc import AgentState
from bd_law_multi_agent.services.legal_service import LegalAnalyzer
from bd_law_multi_agent.services.rag_service import PersistentLegalRAG
from bd_law_multi_agent.prompts.case_analysis_prompt import CASE_ANALYSIS_PROMPT

# Initialize RAG system
rag_system = PersistentLegalRAG()

def _stream_llm_content(llm_stream_method, prompt_str: str) -> Generator[str, None, None]:
    """Helper to stream content from an LLM stream method."""
    try:
        for chunk in llm_stream_method(prompt_str):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content
            elif isinstance(chunk, str): # If the stream directly yields strings
                 yield chunk
    except Exception as e:
        logger.error(f"LLM stream failed: {e}")
        yield f"Error: Could not generate stream: {str(e)}"

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
    # LegalAnalyzer.classify_case returns a Dict, not a stream
    classification = LegalAnalyzer.classify_case(
        state["query"], 
        context=context
    )
    return {"classification": classification, "current_step": "classified_case"}

def generate_analysis(state: AgentState):
    logger.info("Generating legal analysis (streaming)...")
    context = "\n\n".join([
        f"Source: {doc.metadata.get('source_path', 'Unknown')}\nContent: {doc.page_content[:500]}" # Used source_path for consistency
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
    
    # rag_system.llm is the ChatGroq instance, use its stream method
    analysis_generator = _stream_llm_content(rag_system.llm.stream, prompt)
    return {"analysis": analysis_generator, "current_step": "generated_analysis_streaming"}

def generate_follow_ups(state: AgentState):
    logger.info("Generating follow-up questions (handling streamed analysis)...")
    
    analysis_input = state["analysis"]
    analysis_text_collected = ""

    if hasattr(analysis_input, '__iter__') and not isinstance(analysis_input, str):
        logger.info("Consuming analysis stream for follow-up question generation...")
        for chunk in analysis_input:
            analysis_text_collected += chunk
        logger.info(f"Analysis stream consumed. Length: {len(analysis_text_collected)}")
    else:
        analysis_text_collected = analysis_input # It's already a string

    history_for_followups = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": msg} 
        for i, msg in enumerate(state.get("conversation_history", []) or []) # Ensure history is a list
    ] if state.get("conversation_history") else []
    
    # LegalAnalyzer.generate_follow_up_questions returns a generator
    follow_ups_generator = LegalAnalyzer.generate_follow_up_questions(
        analysis_text_collected, 
        history_for_followups
    )
    return {
        "analysis": analysis_text_collected, # Store consumed analysis string back to state
        "follow_ups": follow_ups_generator, 
        "current_step": "generated_follow_ups_streaming"
    }

def generate_legal_argument(state: AgentState):
    logger.info("Generating legal argument (streaming)...")
    try:
        case_details = state["analysis"]  
        if hasattr(case_details, '__iter__') and not isinstance(case_details, str):
            logger.warning("generate_legal_argument received 'analysis' as a stream. Consuming it now.")
            case_details = "".join([chunk for chunk in case_details])

        classification = state["classification"]
       
        docs = rag_system.vector_store.similarity_search(
            case_details,
            k=config.MAX_RETRIEVED_DOCS,
            similarity_threshold=0.75
        )
        
        context_for_argument = "\n\n".join([
            f"Source: {doc.metadata.get('source_path', 'Unknown')}\nContent:{doc.page_content[:config.CITATION_LENGTH]}" # Used source_path
            for doc in docs
        ])
       
        # LegalAnalyzer.generate_legal_argument returns a generator
        argument_generator = LegalAnalyzer.generate_legal_argument(
            case_details=case_details,
            context=context_for_argument,
            category=classification["primary_category"]
        )
        return {
            "documents": docs,  
            "argument": argument_generator,  
            "legal_category": classification["primary_category"],
            "current_step": "generated_argument_streaming"
        }
    except Exception as e:
        logger.error(f"Argument generation failed: {e}")
        def error_gen(msg): yield msg
        return {
            "argument": error_gen(f"Error during argument generation: {str(e)}"), 
            "error_message": str(e), # Changed from 'error' to avoid conflict with graph error field
            "current_step": "generated_argument_error"
            }

def update_history(state: AgentState):
    logger.info("Updating conversation history (handling streamed content)...")
    
    analysis_val = state.get("analysis", "")
    argument_val = state.get("argument", "")

    collected_analysis = ""
    if isinstance(analysis_val, str):
        collected_analysis = analysis_val
    elif hasattr(analysis_val, '__iter__'):
        logger.info("Consuming analysis stream for history...")
        collected_analysis = "".join([chunk for chunk in analysis_val])
        logger.info("Analysis stream consumed for history.")
    
    collected_argument = ""
    if isinstance(argument_val, str):
        collected_argument = argument_val
    elif hasattr(argument_val, '__iter__'):
        logger.info("Consuming argument stream for history...")
        collected_argument = "".join([chunk for chunk in argument_val])
        logger.info("Argument stream consumed for history.")

    response_content = collected_analysis if collected_analysis else collected_argument
    
    current_history = state.get("conversation_history", []) or []
    new_history = current_history + [
        state["query"],
        response_content
    ]

    updates = {
            "conversation_history": new_history, 
            "current_step": "updated_history_streaming",
            "documents": state.get("documents", []) 
        }
    if collected_analysis and not isinstance(analysis_val, str):
        updates["analysis"] = collected_analysis #
    if collected_argument and not isinstance(argument_val, str):
        updates["argument"] = collected_argument 
        
    return updates


def should_continue(state: AgentState):
    # This logic might need adjustment if query processing changes due to streaming
    if "follow_up" in state["query"].lower(): # Assuming query is always a string
        return "continue_analysis"
    return "end"


def create_legal_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("retrieve", retrieve_documents)
    workflow.add_node("classify", classify_case)
    workflow.add_node("analyze", generate_analysis) # Now streams 'analysis'
    workflow.add_node("followups", generate_follow_ups) # Consumes 'analysis', streams 'follow_ups'
    workflow.add_node("update_history", update_history) # Consumes streams for history
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "classify")
    workflow.add_edge("classify", "analyze")
    workflow.add_edge("analyze", "followups")  
    workflow.add_edge("followups", "update_history")
    workflow.add_conditional_edges(
        "update_history",
        should_continue,
        {"continue_analysis": "retrieve", "end": END}
    )
    workflow.add_conditional_edges(
        "retrieve", # This was an unconditional edge to classify before, now conditional on error
        lambda s: "end" if s.get("error_message") else "classify", # Check for error_message
         {"end": END, "classify": "classify"} # Explicitly map outcomes
    )
    return workflow.compile()

def create_argument_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("retrieve", retrieve_documents)
    workflow.add_node("classify", classify_case)
    # 'analyze' node is part of LegalAnalyzer called by generate_legal_argument if needed
    # The generate_legal_argument node itself will use the streamed LegalAnalyzer.generate_legal_argument
    workflow.add_node("argument_generate", generate_legal_argument) # Streams 'argument'
    workflow.add_node("update_history", update_history) # Consumes streams for history
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "classify")
    workflow.add_edge("classify", "argument_generate")
    workflow.add_edge("argument_generate", "update_history")
    workflow.add_conditional_edges(
        "update_history",
        should_continue,
        {"continue_analysis": "retrieve", "end": END}
    )
    workflow.add_conditional_edges(
        "retrieve",
        lambda s: "end" if s.get("error_message") else "classify",
        {"end": END, "classify": "classify"}
    )
    return workflow.compile()

argument_agent = create_argument_workflow()
legal_agent = create_legal_workflow()






