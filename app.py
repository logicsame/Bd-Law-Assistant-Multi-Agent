import streamlit as st
import requests
import json
import os
import pandas as pd
from datetime import datetime
import time
import base64

# API URL - Change for production
API_URL = "http://localhost:8000/api/v1"

# Set page config
st.set_page_config(
    page_title="BD Law Legal Analysis System",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'selected_history_id' not in st.session_state:
    st.session_state.selected_history_id = None
if 'history_data' not in st.session_state:
    st.session_state.history_data = None

# Helper functions
def login_user(email, password):
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            data={"username": email, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            
            # Get user info
            get_user_info()
            # Fetch history after login
            fetch_history()
            return True, "Login successful!"
        else:
            error_detail = response.json().get("detail", "Login failed. Please check your credentials.")
            return False, error_detail
    except Exception as e:
        return False, f"Error connecting to server: {str(e)}"

def register_user(email, password, full_name):
    try:
        response = requests.post(
            f"{API_URL}/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": full_name,
                "is_active": True
            }
        )
        
        if response.status_code == 200:
            return True, "Registration successful! Please login."
        else:
            error_detail = response.json().get("detail", "Registration failed.")
            return False, error_detail
    except Exception as e:
        return False, f"Error connecting to server: {str(e)}"

def get_user_info():
    if st.session_state.token:
        try:
            response = requests.get(
                f"{API_URL}/auth/me",
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            
            if response.status_code == 200:
                st.session_state.user = response.json()
                st.session_state.is_admin = st.session_state.user.get("is_admin", False)
                return True
            else:
                st.session_state.token = None
                st.session_state.user = None
                st.session_state.is_admin = False
                return False
        except:
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.is_admin = False
            return False
    return False

def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.is_admin = False
    st.session_state.history_data = None
    st.session_state.selected_history_id = None
    st.rerun()

def upload_document(file, description=""):
    try:
        files = {"file": (file.name, file, "application/pdf")}
        data = {"description": description}
        
        response = requests.post(
            f"{API_URL}/upload",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        
        if response.status_code == 200:
            # Refresh history after upload
            fetch_history()
            return True, "Document uploaded successfully!", response.json()
        else:
            error_detail = response.json().get("detail", "Upload failed.")
            return False, error_detail, None
    except Exception as e:
        return False, f"Error uploading document: {str(e)}", None

def analyze_document(file):
    try:
        files = {"file": (file.name, file, "application/pdf")}
        
        with st.spinner("Analyzing document..."):
            response = requests.post(
                f"{API_URL}/analyze",
                files=files,
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
        
        if response.status_code == 200:
            # Refresh history after analysis
            fetch_history()
            return True, "Analysis completed successfully!", response.json()
        else:
            error_detail = response.json().get("detail", "Analysis failed.")
            return False, error_detail, None
    except Exception as e:
        return False, f"Error analyzing document: {str(e)}", None

def fetch_history():
    """Fetch user history and store in session state"""
    if st.session_state.token:
        try:
            response = requests.get(
                f"{API_URL}/auth/history",
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            
            if response.status_code == 200:
                st.session_state.history_data = response.json()
                return True
            else:
                st.session_state.history_data = []
                return False
        except Exception:
            st.session_state.history_data = []
            return False
    return False

def get_user_history():
    """Get history data, return from session state if available"""
    if st.session_state.history_data is None:
        fetch_history()
    
    return True, st.session_state.history_data if st.session_state.history_data is not None else []

def promote_to_admin(email):
    try:
        response = requests.post(
            f"{API_URL}/auth/promote-to-admin",
            data={"email": email},
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        
        if response.status_code == 200:
            return True, "User promoted to admin successfully!"
        else:
            error_detail = response.json().get("detail", "Promotion failed.")
            return False, error_detail
    except Exception as e:
        return False, f"Error promoting user: {str(e)}"

def format_datetime(dt_str):
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%b %d, %Y %H:%M")  # More compact format for sidebar
    except:
        return dt_str

def get_file_extension_icon(filename):
    """Return an emoji icon based on file extension"""
    lower_filename = filename.lower()
    if lower_filename.endswith('.pdf'):
        return "📄"
    elif lower_filename.endswith(('.doc', '.docx')):
        return "📝"
    elif lower_filename.endswith('.txt'):
        return "📋"
    else:
        return "📁"

def select_history_item(history_id):
    """Set the selected history item in session state"""
    st.session_state.selected_history_id = history_id
    st.rerun()

# # Custom CSS for styling
# st.markdown("""
# <style>
#     .history-item {
#         padding: 10px;
#         border-left: 3px solid #1E88E5;
#         background-color: #f5f5f5;
#         margin-bottom: 8px;
#         border-radius: 0 4px 4px 0;
#         cursor: pointer;
#         transition: all 0.2s;
#     }
#     .history-item:hover {
#         background-color: #e1f5fe;
#         border-left-color: #039BE5;
#     }
#     .history-item.active {
#         background-color: #e1f5fe;
#         border-left-color: #01579B;
#         font-weight: bold;
#     }
#     .history-date {
#         font-size: 0.8em;
#         color: #757575;
#         display: block;
#     }
#     .history-title {
#         font-weight: 500;
#         margin-bottom: 4px;
#         white-space: nowrap;
#         overflow: hidden;
#         text-overflow: ellipsis;
#     }
#     .sidebar-header {
#         font-size: 1.5em;
#         font-weight: bold;
#         margin-bottom: 20px;
#         color: #01579B;
#     }
#     .history-section {
#         margin-top: 20px;
#         margin-bottom: 10px;
#         font-weight: 500;
#         color: #424242;
#     }
#     .main-header {
#         font-size: 2em;
#         font-weight: bold;
#         color: #01579B;
#         margin-bottom: 20px;
#     }
#     .subheader {
#         font-size: 1.5em;
#         font-weight: bold;
#         color: #424242;
#         margin-bottom: 15px;
#     }
#     .card {
#         background-color: #fff;
#         padding: 20px;
#         border-radius: 5px;
#         box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
#         margin-bottom: 20px;
#     }
#     .no-history {
#         color: #757575;
#         font-style: italic;
#         text-align: center;
#         padding: 10px;
#     }
# </style>
# """, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown('<p class="sidebar-header">BD Law Legal Analysis</p>', unsafe_allow_html=True)
    
    if st.session_state.token:
        st.success(f"Logged in as: {st.session_state.user['email']}")
        
        if st.session_state.is_admin:
            st.info("Admin Access Granted")
        
        # History section in sidebar
        st.markdown('<p class="history-section">Analysis History</p>', unsafe_allow_html=True)
        
        # Fetch and display history
        success, history_data = get_user_history()
        
        if success and history_data:
            # Sort history by date (newest first)
            sorted_history = sorted(history_data, key=lambda x: x.get('created_at', ''), reverse=True)
            
            for item in sorted_history:
                # Create clickable history items
                file_name = item.get('case_file_name', 'Unnamed Document')
                file_date = format_datetime(item.get('created_at', ''))
                file_id = item.get('id')
                file_icon = get_file_extension_icon(file_name)
                
                # Determine if this item is selected
                is_active = st.session_state.selected_history_id == file_id
                active_class = "active" if is_active else ""
                
                # Create the clickable history item
                history_html = f"""
                <div class="history-item {active_class}" onclick="parent.postMessage({{action: 'selectHistoryItem', id: '{file_id}'}}, '*')">
                    <div class="history-title">{file_icon} {file_name}</div>
                    <span class="history-date">{file_date}</span>
                </div>
                """
                st.markdown(history_html, unsafe_allow_html=True)
                
                # Hidden button to handle the click event from JavaScript
                if st.button(f"Select {file_id}", key=f"btn_{file_id}"):
                    select_history_item(file_id)
        else:
            st.markdown('<div class="no-history">No analysis history</div>', unsafe_allow_html=True)
        
        # Refresh history button
        if st.button("Refresh History"):
            fetch_history()
            st.rerun()
        
        # Logout button at bottom of sidebar
        st.markdown("<br><br>", unsafe_allow_html=True)  # Add space
        if st.button("Logout"):
            logout()
    else:
        st.warning("Please login to continue")

# Main content
if not st.session_state.token:
    # Authentication page
    st.markdown('<h1 class="main-header">BD Law Legal Analysis System</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="subheader">Login</p>', unsafe_allow_html=True)
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", key="login_button"):
            if not email or not password:
                st.error("Please enter email and password")
            else:
                success, message = login_user(email, password)
                if success:
                    st.success(message)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(message)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="subheader">Register</p>', unsafe_allow_html=True)
        full_name = st.text_input("Full Name", key="reg_name")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
        
        if st.button("Register", key="register_button"):
            if not email or not password or not full_name:
                st.error("Please fill all required fields")
            elif password != confirm_password:
                st.error("Passwords do not match")
            else:
                success, message = register_user(email, password, full_name)
                if success:
                    st.success(message)
                else:
                    st.error(message)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # Main application
    st.markdown('<h1 class="main-header">BD Law Legal Analysis System</h1>', unsafe_allow_html=True)
    
    # Check if a history item is selected
    if st.session_state.selected_history_id:
        # Display the selected history item
        selected_entry = next((item for item in st.session_state.history_data if item["id"] == st.session_state.selected_history_id), None)
        
        if selected_entry:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<p class="subheader">Analysis: {selected_entry["case_file_name"]}</p>', unsafe_allow_html=True)
            
            # Show document name and date
            st.write(f"**Document:** {selected_entry['case_file_name']}")
            st.write(f"**Date:** {format_datetime(selected_entry['created_at'])}")
            
            # Create tabs for different sections
            detail_tabs = st.tabs(["Analysis", "Original Document"])
            
            with detail_tabs[0]:
                if isinstance(selected_entry['agent_response'], dict) and 'analysis' in selected_entry['agent_response']:
                    st.markdown(selected_entry['agent_response']['analysis'])
                    
                    # Show classification if available
                    if 'classification' in selected_entry['agent_response']:
                        with st.expander("Classification Details"):
                            classification = selected_entry['agent_response']['classification']
                            for category, details in classification.items():
                                st.subheader(category.replace("_", " ").title())
                                if isinstance(details, dict):
                                    for subcategory, value in details.items():
                                        st.write(f"**{subcategory.replace('_', ' ').title()}:** {value}")
                                else:
                                    st.write(details)
                else:
                    st.json(selected_entry['agent_response'])
            
            with detail_tabs[1]:
                st.text_area("Document Content", selected_entry['case_file_content'], height=400)
                
                # Add download button for document content
                document_content = selected_entry['case_file_content']
                b64 = base64.b64encode(document_content.encode()).decode()
                filename = selected_entry['case_file_name']
                download_link = f'<a href="data:text/plain;base64,{b64}" download="{filename}_text.txt">Download as Text File</a>'
                st.markdown(download_link, unsafe_allow_html=True)
            
            # Button to return to main view
            if st.button("Back to Main View"):
                st.session_state.selected_history_id = None
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Standard tab view when no history item is selected
        tabs = ["Document Analysis", "History", "Admin Panel"] if st.session_state.is_admin else ["Document Analysis", "History"]
        selected_tab = st.tabs(tabs)
        
        # Document Analysis Tab
        with selected_tab[0]:
            st.markdown('<p class="subheader">Analyze Legal Documents</p>', unsafe_allow_html=True)
            st.markdown('<div class="card">', unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader("Upload PDF for analysis", type=["pdf"])
            
            if uploaded_file is not None:
                if st.button("Start Analysis"):
                    success, message, analysis_result = analyze_document(uploaded_file)
                    
                    if success:
                        st.success(message)
                        
                        # Display analysis results
                        st.markdown("### Analysis Results")
                        
                        with st.expander("Document Analysis", expanded=True):
                            st.markdown(analysis_result["analysis"])
                        
                        with st.expander("Classification Details", expanded=False):
                            classification = analysis_result["classification"]
                            for category, details in classification.items():
                                st.subheader(category.replace("_", " ").title())
                                if isinstance(details, dict):
                                    for subcategory, value in details.items():
                                        st.write(f"**{subcategory.replace('_', ' ').title()}:** {value}")
                                else:
                                    st.write(details)
                        
                        if analysis_result.get("follow_up_questions"):
                            with st.expander("Follow-up Questions", expanded=False):
                                for idx, question in enumerate(analysis_result["follow_up_questions"], 1):
                                    st.write(f"{idx}. {question}")
                        
                        if analysis_result.get("sources"):
                            with st.expander("Sources", expanded=False):
                                for source in analysis_result["sources"]:
                                    st.markdown(f"""
                                    **Source:** {source['source']}  
                                    **Page:** {source['page']}  
                                    **Excerpt:** {source['excerpt']}  
                                    ---
                                    """)
                        
                        if analysis_result.get("trace_url"):
                            st.markdown(f"[View detailed analysis trace]({analysis_result['trace_url']})")
                    else:
                        st.error(message)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # History Tab
        with selected_tab[1]:
            st.markdown('<p class="subheader">Analysis History</p>', unsafe_allow_html=True)
            
            if st.button("Refresh History Table"):
                fetch_history()
                st.rerun()
            
            success, history_data = get_user_history()
            
            if success:
                if not history_data:
                    st.info("No analysis history found.")
                else:
                    # Create a clean dataframe
                    history_df = pd.DataFrame(history_data)
                    
                    # Create a simplified view for the main table
                    simplified_df = pd.DataFrame({
                        "ID": history_df["id"],
                        "Document Name": history_df["case_file_name"],
                        "Analysis Date": history_df["created_at"].apply(format_datetime)
                    })
                    
                    # Show the table
                    st.dataframe(simplified_df, use_container_width=True)
                    
                    # Detail view for selected entry
                    selected_id = st.selectbox("Select an entry to view details:", simplified_df["ID"])
                    
                    if selected_id:
                        selected_entry = next((item for item in history_data if item["id"] == selected_id), None)
                        
                        if selected_entry:
                            st.markdown('<div class="card">', unsafe_allow_html=True)
                            st.subheader("Analysis Details")
                            
                            # Show document name and date
                            st.write(f"**Document:** {selected_entry['case_file_name']}")
                            st.write(f"**Date:** {format_datetime(selected_entry['created_at'])}")
                            
                            # Create tabs for different sections
                            detail_tabs = st.tabs(["Analysis", "Original Document"])
                            
                            with detail_tabs[0]:
                                if isinstance(selected_entry['agent_response'], dict) and 'analysis' in selected_entry['agent_response']:
                                    st.markdown(selected_entry['agent_response']['analysis'])
                                    
                                    # Show classification if available
                                    if 'classification' in selected_entry['agent_response']:
                                        with st.expander("Classification Details"):
                                            classification = selected_entry['agent_response']['classification']
                                            for category, details in classification.items():
                                                st.subheader(category.replace("_", " ").title())
                                                if isinstance(details, dict):
                                                    for subcategory, value in details.items():
                                                        st.write(f"**{subcategory.replace('_', ' ').title()}:** {value}")
                                                else:
                                                    st.write(details)
                                else:
                                    st.json(selected_entry['agent_response'])
                            
                            with detail_tabs[1]:
                                st.text_area("Document Content", selected_entry['case_file_content'], height=400)
                                
                                # Add download button for document content
                                document_content = selected_entry['case_file_content']
                                b64 = base64.b64encode(document_content.encode()).decode()
                                filename = selected_entry['case_file_name']
                                download_link = f'<a href="data:text/plain;base64,{b64}" download="{filename}_text.txt">Download as Text File</a>'
                                st.markdown(download_link, unsafe_allow_html=True)
                            
                            st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error(f"Failed to retrieve history: {history_data}")
        
        # Admin Tab (only visible to admins)
        if st.session_state.is_admin and len(selected_tab) > 2:
            with selected_tab[2]:
                st.markdown('<p class="subheader">Admin Panel</p>', unsafe_allow_html=True)
                
                admin_tabs = st.tabs(["Upload Knowledge Base", "User Management"])
                
                with admin_tabs[0]:
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.subheader("Upload Knowledge Base Document")
                    
                    kb_file = st.file_uploader("Upload Document", type=["pdf", "docx", "txt"])
                    description = st.text_input("Document Description")
                    
                    if kb_file is not None and st.button("Upload to Knowledge Base"):
                        success, message, doc_data = upload_document(kb_file, description)
                        
                        if success:
                            st.success(message)
                            
                            # Show document details
                            st.json(doc_data)
                        else:
                            st.error(message)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with admin_tabs[1]:
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.subheader("Promote User to Admin")
                    
                    user_email = st.text_input("User Email")
                    
                    if user_email and st.button("Promote to Admin"):
                        success, message = promote_to_admin(user_email)
                        
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("© 2025 BD Law Multi-Agent Legal Analysis System")

# JavaScript for handling history item clicks
components_js = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    // This will handle clicks on the history items
    document.querySelectorAll('.history-item').forEach(function(item) {
        item.addEventListener('click', function() {
            const id = this.getAttribute('data-id');
            if (id) {
                // Find and click the associated hidden button
                document.querySelector('button[key="btn_' + id + '"]').click();
            }
        });
    });
});
</script>
"""

# Use the correct components method
import streamlit.components.v1 as components
components.html(components_js, height=0)