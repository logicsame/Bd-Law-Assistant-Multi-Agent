# conflict_detection_workflow.py
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langsmith import traceable
import uuid
from bd_law_multi_agent.utils.logger import logger
from bd_law_multi_agent.services.conflict_detection import ConflictDetectionService
from bd_law_multi_agent.services.mistral_ocr import MistralOCRTextExtractor
from bd_law_multi_agent.services.analyze_vector_db import AnalysisVectorDB
from bd_law_multi_agent.core.common import extract_case_title, extract_case_parties


conflict_service = ConflictDetectionService()
analysis_db = AnalysisVectorDB()


class ConflictDetectionState(TypedDict):
    """Schema for the conflict detection workflow state"""
    file_content: bytes
    file_name: str
    extracted_text: str
    case_title: str
    case_parties: List[str]
    entities: List[str]
    similarity_threshold: float
    conflicts: List[Dict[str, Any]]
    explanation: str
    conflicts_detected: bool
    current_step: str
    current_file_id: str
    error: str
    trace_url: str

# Node functions for the workflow
@traceable(name="extract_text_from_pdf")
def extract_text_from_pdf(state: ConflictDetectionState, **kwargs) -> ConflictDetectionState:
    """Extract text content from PDF file"""
    try:
        logger.info(f"Extracting text from PDF: {state['file_name']}")
        extractor = MistralOCRTextExtractor()
        if "file_path" in state:
            extracted_text = extractor.extract_text_from_file(state["file_path"])
        elif "file_content" in state and isinstance(state["file_content"], bytes):
            signed_url = extractor.upload_pdf(state["file_content"], state["file_name"])
            document_source = {"type": "document_url", "document_url": signed_url}
            extracted_text = extractor._extract_text_from_source(document_source)
        else:
            return {
                **state,
                "error": "Missing file_path or file_content in state",
                "current_step": "error"
            } 
        if not extracted_text.strip():
            return {
                **state,
                "error": "No text extracted from PDF",
                "current_step": "error"
            }
        return {
            **state,
            "extracted_text": extracted_text,
            "current_step": "extract_entities"
        }
    except Exception as e:
        logger.error(f"PDF extraction failed: {str(e)}")
        return {
            **state,
            "error": f"PDF extraction failed: {str(e)}",
            "current_step": "error"
        }

@traceable(name="extract_case_information")
def extract_case_information(state: ConflictDetectionState, **kwargs) -> ConflictDetectionState:
    """Extract case title and parties from the document"""
    try:
        # Extract case title and parties
        case_title = extract_case_title(state["extracted_text"])
        case_parties = extract_case_parties(state["extracted_text"])
        
        logger.info(f"Extracted case information: {case_title}")
        
        return {
            **state,
            "case_title": case_title or "",
            "case_parties": case_parties,
            "current_step": "extract_entities"
        }
        
    except Exception as e:
        logger.error(f"Case info extraction failed: {str(e)}")
        return {
            **state,
            "case_title": "",
            "case_parties": [],
            "current_step": "extract_entities"  # Continue even if this fails
        }

@traceable(name="extract_entities")
def extract_entities(state: ConflictDetectionState, **kwargs) -> ConflictDetectionState:
    """Extract named entities from the document text"""
    try:
        logger.info("Extracting and cleaning entities...")
        entities = conflict_service.extract_entities(state["extracted_text"])
        
        # Add case title and parties to entities if not already present
        if state["case_title"] and state["case_title"] not in entities:
            entities.append(state["case_title"])
            
        for party in state["case_parties"]:
            if party and party not in entities:
                entities.append(party)
        
        # Remove duplicates and sort by length (longer entities first)
        entities = sorted(list(set(entities)), key=len, reverse=True)
        
        logger.info(f"Found {len(entities)} entities: {', '.join(entities[:5])}...")
        
        if not entities:
            return {
                **state,
                "entities": [],
                "conflicts_detected": False,
                "explanation": "No valid entities found for conflict checking",
                "current_step": "generate_response"
            }
            
        return {
            **state,
            "entities": entities,
            "current_step": "check_conflicts"
        }
        
    except Exception as e:
        logger.error(f"Entity extraction failed: {str(e)}")
        return {
            **state,
            "error": f"Entity extraction failed: {str(e)}",
            "current_step": "error"
        }

@traceable(name="check_conflicts")
def check_conflicts(state: ConflictDetectionState, **kwargs) -> ConflictDetectionState:
    """Check for conflicts with entities against the analysis database"""
    try:
        # Get document count to determine if DB is empty
        doc_count = analysis_db.get_document_count()
        logger.info(f"Current document count in DB: {doc_count}")
        
        conflicts = []
        
        if doc_count > 0: 
            from bd_law_multi_agent.core.common import check_conflicts_in_raw_cases
            
            conflicts = check_conflicts_in_raw_cases(
                entities=state["entities"],
                similarity_threshold=state["similarity_threshold"],
                current_file_id=state["current_file_id"]
            )
        else:
            logger.warning("No documents in database, skipping conflict check")
            
        return {
            **state,
            "conflicts": conflicts,
            "conflicts_detected": len(conflicts) > 0,
            "current_step": "generate_explanation"
        }
        
    except Exception as e:
        logger.error(f"Conflict check failed: {str(e)}")
        return {
            **state,
            "error": f"Conflict check failed: {str(e)}",
            "current_step": "error"
        }

@traceable(name="generate_explanation")
def generate_explanation(state: ConflictDetectionState, **kwargs) -> ConflictDetectionState:
    """Generate human-readable explanation of conflicts or clearance"""
    try:
        # Generate explanation of conflicts
        explanation = conflict_service.generate_conflict_explanation(state["conflicts"])
        
        return {
            **state,
            "explanation": explanation,
            "current_step": "generate_response"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate explanation: {str(e)}")
        return {
            **state,
            "explanation": "Failed to generate detailed explanation of conflicts",
            "current_step": "generate_response"  # Continue to response generation
        }

@traceable(name="generate_response")
def generate_response(state: ConflictDetectionState, **kwargs) -> ConflictDetectionState:
    """Format the final response"""
    # This node just transitions to the end
    return {
        **state,
        "current_step": "end"
    }

@traceable(name="handle_error")
def handle_error(state: ConflictDetectionState, **kwargs) -> ConflictDetectionState:
    """Handle errors in the workflow"""
    logger.error(f"Workflow error: {state.get('error', 'Unknown error')}")
    return {
        **state,
        "current_step": "end"
    }

# Define the workflow graph
def create_conflict_detection_graph():
    """Create and configure the conflict detection workflow graph"""
    
    # Create a new graph
    workflow = StateGraph(ConflictDetectionState)
    
    # Add nodes to the graph
    workflow.add_node("extract_text", extract_text_from_pdf)
    workflow.add_node("extract_case_info", extract_case_information)
    workflow.add_node("extract_entities", extract_entities)
    workflow.add_node("check_conflicts", check_conflicts)
    workflow.add_node("generate_explanation", generate_explanation)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("handle_error", handle_error)
    
    # Define workflow transitions
    workflow.add_edge("extract_text", "extract_case_info")
    workflow.add_edge("extract_case_info", "extract_entities")
    workflow.add_edge("extract_entities", "check_conflicts")
    workflow.add_edge("check_conflicts", "generate_explanation")
    workflow.add_edge("generate_explanation", "generate_response")
    workflow.add_edge("generate_response", END)
    
    # Error handling
    workflow.add_conditional_edges(
        "extract_text",
        lambda state: "handle_error" if state.get("error") else "extract_case_info",
        {
            "handle_error": "handle_error",
            "extract_case_info": "extract_case_info"
        }
    )
    
    workflow.add_edge("handle_error", END)
    
    # Set the entry point
    workflow.set_entry_point("extract_text")
    
    return workflow.compile()

# Create the compiled workflow
conflict_detection_agent = create_conflict_detection_graph()

# Traceable function to invoke the workflow
@traceable(name="conflict_detection_workflow")
def detect_conflicts(
    file_content: bytes,
    file_name: str,
    similarity_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Execute the conflict detection workflow
    
    Args:
        file_content: PDF file content as bytes
        file_name: Name of the uploaded file
        similarity_threshold: Threshold for conflict similarity
        
    Returns:
        Dict containing conflict detection results
    """

    if similarity_threshold < 0.65:
        raise ValueError("Threshold too low (<0.65) for reliable conflict detection")

    current_file_id = str(uuid.uuid4())
    initial_state = {
        "file_content": file_content,
        "file_name": file_name,
        "extracted_text": "",
        "case_title": "",
        "case_parties": [],
        "entities": [],
        "similarity_threshold": similarity_threshold,
        "conflicts": [],
        "explanation": "",
        "conflicts_detected": False,
        "current_step": "extract_text",
        "current_file_id": current_file_id,
        "error": "",
        "trace_url": ""
    }

    final_state = conflict_detection_agent.invoke(initial_state)
    return {
        "conflicts_detected": final_state.get("conflicts_detected", False),
        "explanation": final_state.get("explanation", ""),
        "entities_found": final_state.get("entities", []),
        "conflicts": final_state.get("conflicts", []),
        "error": final_state.get("error", ""),
        "trace_url": final_state.get("trace_url", ""),
        "case_title": final_state.get("case_title", ""),
        "extracted_text": final_state.get("extracted_text", "")  

    }