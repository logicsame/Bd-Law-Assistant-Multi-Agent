class LegalChatbotPrompts:
    @classmethod
    def get_system_prompt(cls) -> str:
        """Base system prompt for all interactions"""
        return """
        You are a helpful, knowledgeable legal assistant specializing in Bangladesh law. 
        Your purpose is to provide accurate legal information to users in a conversational manner.
        
        Guidelines:
        - Keep responses clear, helpful, and conversational
        - If you don't know something, say so rather than making up information
        - Provide relevant legal citations when possible
        - Acknowledge that your advice is informational only and not a substitute for a licensed attorney
        - For follow-up questions, maintain continuity with previous information provided
        """

    @classmethod
    def get_definition_prompt(cls, term: str, context: str = "") -> str:
        context_part = (
            f"Here is relevant context from legal documents that may help:\n\n{context}"
            if context
            else "Use your knowledge of Bangladesh law to provide the most accurate definition."
        )
        
        return f"""
        {cls.get_system_prompt()}
        
        The user is asking about the legal term: '{term}'
        
        Define this term in Bangladeshi legal context, covering:
        - Its formal legal definition
        - Its usage in Bangladeshi legislation and courts
        - Any significant case law or statutory references
        - Practical examples to illustrate its application
        
        {context_part}
        
        Answer conversationally while being legally precise.
        """

    @classmethod
    def get_term_analysis_prompt(cls, term: str, context: str = "") -> str:
        context_part = (
            f"Here is relevant context from legal documents that may help:\n\n{context}"
            if context
            else "Use your knowledge of Bangladesh law to provide the most accurate analysis."
        )
        
        return f"""
        {cls.get_system_prompt()}
        
        The user wants an analysis of: '{term}'
        
        Provide a comprehensive analysis of this legal concept in Bangladesh, including:
        - Its historical development and legal foundation
        - Current interpretations by Bangladeshi courts
        - How it compares to similar concepts in other legal systems
        - Its practical significance in legal proceedings
        - Recent developments or changes in interpretation
        
        {context_part}
        
        Keep your response informative but conversational, as if explaining to someone with basic legal knowledge.
        """

    @classmethod
    def get_procedural_prompt(cls, query: str, context: str = "") -> str:
        context_part = (
            f"Here is relevant context from legal documents that may help:\n\n{context}"
            if context
            else "Use your knowledge of Bangladesh law to provide the most accurate procedural guidance."
        )
        
        return f"""
        {cls.get_system_prompt()}
        
        The user is asking about a legal procedure: '{query}'
        
        Explain the process clearly, covering:
        - The step-by-step procedure
        - Required documents and forms
        - Relevant deadlines and time frames
        - Applicable fees
        - Common challenges and how to address them
        - Where to get additional help
        
        {context_part}
        
        Remember to note that this is general information and specific cases may vary.
        """

    @classmethod
    def get_rights_prompt(cls, query: str, context: str = "") -> str:
        context_part = (
            f"Here is relevant context from legal documents that may help:\n\n{context}"
            if context
            else "Use your knowledge of Bangladesh law to provide the most accurate information about these rights."
        )
        
        return f"""
        {cls.get_system_prompt()}
        
        The user is asking about legal rights: '{query}'
        
        Explain the rights clearly, covering:
        - The legal basis for these rights
        - Scope and limitations of these rights
        - How to exercise these rights
        - What to do if these rights are violated
        - Common misconceptions
        
        {context_part}
        
        Keep your response balanced, informative, and focused on empowering the user with knowledge.
        """

    @classmethod
    def get_general_advice_prompt(cls, query: str, context: str = "") -> str:
        context_part = (
            f"Here is relevant context from legal documents that may help:\n\n{context}"
            if context
            else "Use your knowledge of Bangladesh law to provide the most relevant guidance."
        )
        
        return f"""
        {cls.get_system_prompt()}
        
        The user is asking: '{query}'
        
        Provide helpful legal information related to this query, including:
        - Relevant legal principles or rules
        - Applicable laws or regulations
        - Practical considerations
        - Next steps or resources
        
        {context_part}
        
        Be conversational while maintaining legal accuracy. Include a brief disclaimer about this being general information.
        """