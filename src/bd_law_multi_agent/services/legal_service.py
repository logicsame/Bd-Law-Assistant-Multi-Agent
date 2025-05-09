
from __future__ import annotations

import re
from typing import List, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from bd_law_multi_agent.core.common import logger
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.prompts.case_analysis_prompt import CASE_ANALYSIS_PROMPT
from bd_law_multi_agent.prompts.argument_generation_prompt import ArgumentGenerationPrompt
from bd_law_multi_agent.schemas.schemas import CaseClassification 




class LegalAnalyzer:

    @classmethod
    def classify_case(cls, query: str, context: str) -> Dict[str, Any]:
        """
        Classify a matter and return a dictionary that conforms to
        `CaseClassification` (schema in src/schemas/case_classification.py).
        """
        try:
            # llm = ChatOpenAI(
            #     model=config.LLM_MODEL,
            #     temperature=config.TEMPERATURE,
            #     max_tokens=config.MAX_TOKENS,
            # )
            
            llm = ChatGroq(   # <- for temp devlopment
                model = config.GROQ_LLM_MODEL,
                temperature=config.TEMPERATURE
            )

            prompt = CASE_ANALYSIS_PROMPT.get_case_classification_prompt(
                query=query,
                context=context,
                categories=config.CASE_CATEGORIES,
                complexity_levels=config.CASE_SEVERITY_LEVELS,
            )

            raw: str = llm.invoke(prompt).content.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^.*?```(?:json)?(.*?)```.*?$", r"\1", raw, flags=re.DOTALL|re.IGNORECASE).strip()

            try:
                model = CaseClassification.model_validate_json(raw)  # Pydantic v2
                # For Pydantic v1 use: model = CaseClassification.parse_raw(raw)
            except Exception as exc:
                logger.error("Invalid schema from LLM: %s", exc)
                model = CaseClassification()  # defaults defined in the schema

            clean_dict = {
                k: (v if v is not None else "")
                for k, v in model.model_dump().items()  # .dict() for v1
            }
            return clean_dict

        except Exception as exc:
            logger.error("Case classification failed: %s", exc)
            # ultimate fallback — will always satisfy response model
            return CaseClassification().model_dump()

    @classmethod
    def generate_follow_up_questions(
        cls, analysis: str, history: List[Dict]
    ) -> List[str]:
        try:
            # llm = ChatOpenAI(model=config.LLM_MODEL, temperature=config.TEMPERATURE)
            llm = ChatGroq(model = config.GROQ_LLM_MODEL, temperature=config.TEMPERATURE)

            prompt = CASE_ANALYSIS_PROMPT.get_follow_up_prompt().format(
                analysis=analysis,
                history="\n".join(f"{m['role']}: {m['content']}" for m in history),
            )

            resp = llm.invoke(prompt)
            return [q.strip() for q in resp.content.splitlines() if q.strip()]
        except Exception as exc:
            logger.error("Follow-up question generation error: %s", exc)
            return ["Could not generate follow-up questions at this time."]


    @classmethod
    def generate_legal_argument(
        cls, case_details: str, context: str, category: str
    ) -> str:
        try:
            # llm = ChatOpenAI(model=config.LLM_MODEL, temperature=0.3, max_tokens=2048)
            llm = ChatGroq(model = config.GROQ_LLM_MODEL, temperature=config.TEMPERATURE)

            example = ArgumentGenerationPrompt.Example_Arguemnts().get(
                category,
                next(iter(ArgumentGenerationPrompt.Example_Arguemnts().values())),
            )

            prompt = ArgumentGenerationPrompt.Argument_Prompt_Template().format(
                case_details=case_details,
                legal_context=context,
                primary_category=category,
                example_argument=example,
            )

            return llm.invoke(prompt).content
        except Exception as exc:
            logger.error("Argument generation error: %s", exc)
            return "Could not generate argument at this time."
