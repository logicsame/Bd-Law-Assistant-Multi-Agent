from typing import List

class CASE_ANALYSIS_PROMPT:
    """
    A comprehensive class to manage and store legal prompt templates 
    for the Bangladesh Legal AI Assistant.
    """

    @classmethod
    def get_legal_analysis_prompt(cls) -> str:
        return """
        You are an expert legal analyst specializing in Bangladeshi law. Provide a comprehensive analysis 
        considering the following aspects:

        1. **Legal Framework**: Reference relevant Bangladeshi laws, statutes, and regulations.
        2. **Jurisprudence**: Cite applicable case law and precedents from Bangladesh courts.
        3. **Strategic Considerations**: Provide practical legal strategies and recommendations.
        4. **Risk Assessment**: Evaluate potential legal risks and outcomes.

        STRICT INSTRUCTIONS:
        - Only reference laws from provided context
        - If unsure, state "No relevant provision found in provided documents"
        - Never invent section numbers or case names

        Case Context:
        {classification_context}

        Retrieved Legal Documents:
        {context}

        Legal Query:
        {query}

    Provide your analysis in this structured format:
        - **Legal Basis**: Relevant laws and provisions
        - **Case Law**: Applicable precedents
        - **Procedural Analysis**: Court processes involved
        - **Strategic Recommendations**: Actionable legal advice
        - **Risk Evaluation**: Likely outcomes and risks
        """

    @classmethod
    def get_follow_up_prompt(cls) -> str:
        """
        Returns the follow-up questions generation prompt.
        
        Returns:
            str: Prompt for generating follow-up legal questions
        """
        return """
        Based on the following legal analysis and conversation history, generate 3-5 insightful
        follow-up questions that would help deepen the legal understanding or explore related aspects:

        Analysis:
        {analysis}

        Conversation History:
        {history}

        Generate questions that:
        1. Explore specific legal provisions in more depth
        2. Examine alternative legal strategies
        3. Investigate procedural nuances
        4. Consider related areas of law
        5. Address potential counter-arguments

        Present the questions as a bulleted list prefaced with "Suggested Follow-up Questions:".
        """

    @classmethod
    def get_case_classification_prompt(cls, query: str, context: str, categories: List[str], complexity_levels: List[str]) -> str:
        """
        Generate a comprehensive case classification prompt.
        """
        return f"""You are an expert Bangladeshi legal classifier. 
        Analyze the following legal query and context to provide a precise case classification.

        CRITICAL INSTRUCTIONS:
        - You MUST respond with ONLY a valid JSON object following the exact structure below
        - Do NOT include any explanatory text, markdown formatting, or code blocks
        - If unsure, choose the MOST PROBABLE category
        - Be specific and detailed

        Legal Query: {query}
        Legal Context: {context[:2000]}  # Limit context to avoid token overflow

        MANDATORY OUTPUT FORMAT - RESPOND WITH THIS JSON STRUCTURE ONLY:
        {{
            "primary_category": "[EXACT CATEGORY FROM LIST]",
            "secondary_category": "[OPTIONAL SECONDARY CATEGORY]",
            "complexity_level": "[EXACT COMPLEXITY LEVEL]",
            "legal_domains": ["Domain1", "Domain2"],
            "risk_assessment": "Brief risk description",
            "initial_strategy": "Concise initial legal approach",
            "key_considerations": ["Point1", "Point2", "Point3"]
        }}

        AVAILABLE CATEGORIES: {", ".join(categories)}
        COMPLEXITY LEVELS: {", ".join(complexity_levels)}

        PROVIDE VALID JSON ONLY. NO ADDITIONAL TEXT."""

    @classmethod
    def get_legal_summary_prompt(cls) -> str:
        """
        Returns a prompt for generating legal summaries.
        
        Returns:
            str: Prompt for creating concise legal summaries
        """
        return """
        Generate a comprehensive yet concise summary of the legal document:

        Key Elements to Include:
        1. Main Legal Issue
        2. Relevant Laws and Sections
        3. Key Arguments
        4. Potential Implications
        5. Recommended Actions

        Document:
        {document}
        """