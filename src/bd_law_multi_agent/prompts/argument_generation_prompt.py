from typing import List


class ArgumentGenerationPrompt:
    
    @classmethod
    def Argument_Prompt_Template(cla) -> str:
        
        return """
    You are an experienced defense lawyer practicing in Bangladeshi courts. 
    Draft a comprehensive legal argument in the IRAC (Issue, Rule, Application, Conclusion) structure 
    based on the following case details and legal context:

    **Case Details:**
    {case_details}

    **Relevant Legal Context:**
    {legal_context}

    Follow this three-step process:
    
    STEP 1: Analyze the case and identify the 2-3 strongest legal issues in your client's favor.
    
    STEP 2: For each issue:
      - Identify the exact provisions from Bangladeshi laws that support your position
      - Apply logical reasoning to connect the law to the specific facts of this case
      - Anticipate and address the prosecution's likely counter-arguments
    
    STEP 3: Structure your final argument using the IRAC format:
    
    [ISSUES]
    - List each key legal issue as a clear question or statement
    
    [RULES]
    - Cite specific sections of Bangladeshi law with exact section numbers
    - Include relevant case precedents that support your position
    - Quote the actual text of the most important provisions
    
    [APPLICATION]
    - Connect each fact from the case to the relevant law
    - Emphasize facts that strengthen your client's position
    - Address and neutralize facts that may harm your client's position
    - Highlight procedural errors or evidentiary weaknesses in the prosecution's case
    
    [CONCLUSION]
    - State the specific relief you're seeking (acquittal, dismissal, etc.)
    - Summarize the strongest 1-2 points from your argument
    
    Your argument should demonstrate deep knowledge of {primary_category} law while being practical and persuasive for a Bangladeshi court. Focus on local legal principles, not foreign jurisdictions.
    
    Here's an example of a well-structured argument for reference:
    {example_argument}
    """
    
    @classmethod
    def Example_Arguemnts(cls) -> str:
        return  {
        "Criminal Case": """
        [ISSUES]
        1. Whether the prosecution has established mens rea beyond reasonable doubt as required under Section 34 of the Penal Code
        2. Whether the evidence presented meets the burden of proof standard under Section 101 of the Evidence Act
        
        [RULES]
        1. Penal Code Section 34 states: "When a criminal act is done by several persons in furtherance of the common intention of all, each of such persons is liable for that act in the same manner as if it were done by him alone."
        
        2. Evidence Act Section 101 states: "Whoever desires any Court to give judgment as to any legal right or liability dependent on the existence of facts which he asserts, must prove that those facts exist." 
        
        3. In State vs. Rahman (2019 BLD 345), the High Court Division held: "Mere presence at the scene without evidence of participation or prior agreement does not establish common intention under Section 34 of the Penal Code."
        
        [APPLICATION]
        Regarding Issue 1:
        - The prosecution has failed to produce any evidence of prior meeting of minds between my client and the co-accused.
        - Witness statements from Karim and Rahim place my client at the scene but do not establish any act of participation in the alleged offense.
        - Applying the ratio in State vs. Rahman, mere presence without active participation is insufficient to establish liability under Section 34.
        
        Regarding Issue 2:
        - The prosecution's witness statements contradict each other on material particulars:
          * Witness Karim claims the incident occurred at 9:00 PM, while Witness Rahim states it was 10:30 PM
          * Witness descriptions of my client's clothing are inconsistent
        - The forensic report lacks proper chain of custody documentation as required by Evidence Act Section 45
        - No recovery of incriminating materials was made from my client's possession
        
        [CONCLUSION]
        Therefore, I respectfully pray that this Honorable Court acquit my client under Section 265C of the Criminal Procedure Code on the following grounds:
        1. Failure of prosecution to establish common intention under Section 34 of the Penal Code
        2. Failure to meet the burden of proof under Section 101 of the Evidence Act due to material contradictions in witness testimony
        """,
        
        "Property Dispute": """
        [ISSUES]
        1. Whether my client has established valid ownership through proper title documents under Section 54 of the Transfer of Property Act
        2. Whether my client's adverse possession claim satisfies the requirements of Section 28 of the Limitation Act
        
        [RULES]
        1. Transfer of Property Act Section 54 states: "A transfer of ownership of immovable property of the value of one hundred taka and upwards can be made only by a registered instrument."
        
        2. Limitation Act Section 28 states: "At the determination of the period hereby limited to any person for instituting a suit for possession of any property, his right to such property shall be extinguished." This has been judicially interpreted to require 12 years of continuous, open, and hostile possession.
        
        3. In Ali vs. Khan (2020 CLR 12), the Appellate Division held: "Mutation records and tax receipts alone do not constitute conclusive proof of title but may be considered corroborative evidence of possession."
        
        [APPLICATION]
        Regarding Issue 1:
        - My client possesses a properly registered deed dated January 15, 2010, executed by the previous owner Mohammed Ali, which establishes valid transfer under Section 54
        - The deed contains precise property boundaries matching the current physical demarcation
        - All subsequent tax payments have been made by my client as evidenced by municipal records
        
        Regarding Issue 2:
        - Even if the Court finds any defect in the title documents, my client has maintained continuous, open, and exclusive possession of the property since 2008
        - This 15-year period exceeds the 12-year requirement under Section 28 of the Limitation Act
        - The respondent has never challenged this possession until now, demonstrating acquiescence
        - Multiple independent witnesses confirm my client's continuous possession
        
        [CONCLUSION]
        Therefore, I respectfully pray that this Honorable Court:
        1. Declare my client as the rightful owner of the property based on the registered deed and continuous possession
        2. Issue a permanent injunction restraining the respondent from interfering with my client's possession
        """
    }