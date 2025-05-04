# bd_law_multi_agent/utils/common.py
import os
from urllib.parse import urlparse

def get_file_type(filename: str) -> str:
    """
    Determine the type of file based on its extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        String indicating the file type ('pdf', 'image', etc.)
        
    Raises:
        ValueError: If file type is not supported
    """
    if not filename:
        raise ValueError("Filename is required")
        
    # Get the file extension
    _, ext = os.path.splitext(filename.lower())
    
    # Match extension to file type
    if ext == '.pdf':
        return 'pdf'
    elif ext in ['.jpg', '.jpeg', '.png']:
        return 'image'
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported types are: .pdf, .jpg, .jpeg, .png")

def get_url_type(url: str) -> str:
    """
    Determine the type of content a URL points to based on its extension or domain.
    
    Args:
        url: URL string
        
    Returns:
        String indicating the content type ('pdf', 'webpage', etc.)
        
    Raises:
        ValueError: If URL is invalid or points to unsupported content
    """
    if not url:
        raise ValueError("URL is required")
        
    try:
        parsed = urlparse(url)
        
        # Check if URL has a valid scheme
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
            
        # Get the path and check file extension if present
        path = parsed.path.lower()
        
        if path.endswith('.pdf'):
            return 'pdf'
        elif path.endswith(('.jpg', '.jpeg', '.png')):
            return 'image'
        elif parsed.netloc.endswith(('arxiv.org', 'papers.ssrn.com')):
            return 'academic_paper'
        else:
            return 'webpage'
            
    except Exception as e:
        raise ValueError(f"Error parsing URL: {str(e)}")