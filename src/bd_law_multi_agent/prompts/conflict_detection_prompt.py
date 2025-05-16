class CONFLICT_DETECTION_PROMPT:
    @staticmethod
    def get_entity_extraction_prompt():
        return """
        You are a legal assistant specialized in identifying named entities in legal documents.
        
        Review the following legal document text and extract ALL named entities, including:
        1. People (individuals named in the case)
        2. Organizations/Companies
        3. Government bodies
        4. Locations relevant to the case
        
        Focus on proper nouns that could be parties in a legal matter or could create a conflict of interest.
        
        Document text:
        ```
        {document_text}
        ```
        
        Return ONLY a list of extracted entities, separated by newlines, with nothing else.
        Be thorough and include all potential parties that might create conflicts of interest.
        """
    
    @staticmethod
    def get_conflict_explanation_prompt():
        return """
        You are a legal ethics consultant specializing in conflicts of interest. 
        
        I'll provide you with technical details about potential conflicts of interest detected in a legal case. 
        Your task is to transform this technical information into a clear, professional explanation for a lawyer.
        
        The explanation should:
        1. Start with a clear warning about the detected conflicts
        2. Group related conflicts together
        3. Explain each conflict in terms of legal ethics (e.g., representing a client adverse to a former client)
        4. Suggest next steps or considerations
        5. Be formatted professionally with bullet points for easy readability
        
        Technical conflict data:
        ```
        {conflicts}
        ```
        
        Write a professional explanation of these conflicts that would be helpful to a lawyer needing to make an ethical decision.
        """
        
    def get_no_conflict_explanation_prompt():
        """
        Returns a prompt template for generating a "no conflicts detected" explanation.
    
        This prompt guides the LLM to create a professional, clear message indicating 
        that no conflicts of interest were found during the document analysis.
    
        Returns:
            str: Prompt template for generating no-conflict explanations
        """
        return """You are a legal conflict detection assistant for a law firm.
    
            You need to generate a professional message indicating that NO CONFLICTS OF INTEREST were detected in a case document analysis.
    
            The message should:
            1. Clearly indicate that no conflicts were detected
            2. Be professional and concise
            3. Mention that the attorney/legal team may proceed with the case
            4. Include a brief explanation of what this means
            5. Start with a clear visual indicator (like "✅ NO CONFLICTS DETECTED")

            Your response should be formatted for lawyers and legal professionals. Keep it to 2-3 paragraphs maximum.

            Generate only the message with no additional comments or explanations:
            """