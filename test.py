"""
Complete Self-Learning Agent with AutoRL and Web Tools
Fully Functional Implementation
"""

import os
import re
import json
import numpy as np
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Environment setup
from dotenv import load_dotenv
load_dotenv()

# Core LangChain components
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferMemory

# LLM and Tools
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchRun

# Browser automation
from playwright.async_api import async_playwright

# Async compatibility
import nest_asyncio
nest_asyncio.apply()

class AdaptiveRewardModel:
    """Complete reward learning system with persistence"""
    def __init__(self, learning_rate: float = 0.1):
        self.learning_rate = learning_rate
        self.feature_weights = np.array([0.4, 0.3, 0.2, 0.1])  # Initial weights
        self.feedback_history = []
        self.load_model()

    def extract_features(self, action: str) -> np.ndarray:
        """Extract 4 key performance features from agent actions"""
        features = np.zeros(4)
        
        # Feature 1: Response length (normalized)
        features[0] = min(len(action) / 2000, 1.0)
        
        # Feature 2: Error signals
        features[1] = len(re.findall(r'\b(error|sorry|fail|oops)\b', action.lower())) / 3
        
        # Feature 3: Tool usage
        features[2] = 1.0 if any(tool in action.lower() for tool in ['search', 'browse', 'lookup']) else 0.0
        
        # Feature 4: Structured content
        features[3] = (action.count('```') + action.count('<table>')) / 2
        
        return np.clip(features, 0, 1)

    def compute_reward(self, action: str) -> float:
        """Calculate automatic reward score (0-1 scale)"""
        return float(np.dot(self.extract_features(action), self.feature_weights))

    def update_from_feedback(self, action: str, feedback: float):
        """Adapt model weights based on explicit feedback"""
        features = self.extract_features(action)
        adjustment = self.learning_rate * feedback * features
        self.feature_weights = np.clip(self.feature_weights + adjustment, 0, 1)
        self._record_feedback(action, feedback)

    def _record_feedback(self, action: str, feedback: float):
        """Store feedback interaction"""
        self.feedback_history.append({
            "timestamp": datetime.now().isoformat(),
            "action_snippet": action[:300],
            "feedback": feedback,
            "updated_weights": self.feature_weights.tolist()
        })

    def save_model(self, path: str = "reward_model.json"):
        """Persist model to disk"""
        with open(path, 'w') as f:
            json.dump({
                "weights": self.feature_weights.tolist(),
                "history": self.feedback_history[-100:],  # Keep last 100 entries
                "metadata": {
                    "version": "1.0",
                    "last_updated": datetime.now().isoformat()
                }
            }, f, indent=2)

    def load_model(self, path: str = "reward_model.json"):
        """Load model from disk"""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                self.feature_weights = np.array(data['weights'])
                self.feedback_history = data.get('history', [])
        except (FileNotFoundError, json.JSONDecodeError):
            print("No valid reward model found - starting fresh")

class SelfLearningAgent:
    """Complete autonomous agent implementation"""
    def __init__(self, model: str = "gemini-pro", temperature: float = 0.7):
        # Initialize core components
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # Memory and learning
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.reward_model = AdaptiveRewardModel()
        
        # Browser components
        self.playwright = None
        self.browser = None
        self.browser_context = None
        
        # Agent system
        self.tools = self._initialize_tools()
        self.agent_executor = self._create_agent_executor()

    def _initialize_tools(self) -> List[Tool]:
        """Set up agent tools with enhanced capabilities"""
        search_tool = DuckDuckGoSearchRun()
        
        return [
            Tool(
                name="WebSearch",
                func=search_tool.run,
                description=(
                    "Search the web for current information. "
                    "Use for facts, news, or real-time data. "
                    "Input should be a clear search query."
                )
            ),
            Tool(
                name="Browser",
                func=self._execute_browser_action,
                description=(
                    "Interact with websites. Can extract content or navigate. "
                    "Input should be a URL or specific instruction like "
                    "'get headlines from https://news.com'."
                )
            )
        ]

    async def _execute_browser_action(self, instruction: str) -> str:
        """Handle all browser automation commands"""
        if not self.browser:
            return "Browser not initialized"
        
        try:
            # Simple page navigation
            if instruction.startswith(('http://', 'https://')):
                await self.browser.goto(instruction)
                content = await self.browser.content()
                return f"Page content (truncated): {content[:3000]}..."
            
            # Content extraction
            elif 'extract' in instruction.lower():
                selector = re.search(r'selector:([^\n]+)', instruction)
                if selector:
                    elements = await self.browser.query_selector_all(selector.group(1).text_content())
                    return f"Extracted content: {', '.join(elements[:5])}..."
                return "Please specify a CSS selector for extraction"
            
            return "Valid browser commands: URL navigation or 'extract with selector:...'"
        except Exception as e:
            return f"Browser error: {str(e)}"

    def _create_agent_executor(self) -> AgentExecutor:
        """Configure the complete agent system"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are an adaptive AI assistant that improves through experience. "
                "Guidelines:\n"
                "1. Use tools when needed\n"
                "2. Be concise but thorough\n"
                "3. Admit when unsure\n"
                "4. Learn from feedback\n\n"
                "Tools Available:\n"
                "{tools}\n\n"
                "Response Format:\n"
                "Thought: Consider needed actions\n"
                "Action: Use tool if required\n"
                "Observation: Tool results\n"
                "Final Answer: Complete response"
            )),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors="Check your output and try again"
        )

    async def initialize_browser(self):
        """Set up Playwright browser instance"""
        try:
            self.playwright = await async_playwright().start()
            browser = await self.playwright.chromium.launch(headless=True)
            self.browser_context = await browser.new_context()
            self.browser = await self.browser_context.new_page()
            await self.browser.goto('about:blank')  # Initial page
            print("Browser initialized successfully")
        except Exception as e:
            print(f"Browser initialization failed: {str(e)}")
            self.browser = None

    async def process_query(self, query: str) -> Dict[str, Any]:
        """Complete query processing with learning integration"""
        try:
            # Execute the query
            result = await self.agent_executor.ainvoke({"input": query})
            
            # Calculate automatic reward
            reward = self.reward_model.compute_reward(result['output'])
            
            # Store interaction
            self.memory.save_context(
                {"input": query},
                {"output": result['output']}
            )
            
            return {
                "success": True,
                "query": query,
                "response": result['output'],
                "reward": reward,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "reward": -1.0
            }

    def integrate_feedback(self, query: str, rating: float):
        """Process explicit user feedback"""
        history = self.memory.load_memory_variables({})
        last_response = next(
            (msg.content for msg in reversed(history['chat_history']) if isinstance(msg, AIMessage)),
        ""
        )
        self.reward_model.update_from_feedback(last_response, rating)
        self.reward_model.save_model()

    async def shutdown(self):
        """Complete cleanup of resources"""
        if self.browser:
            await self.browser.close()
            await self.browser_context.close()
            await self.playwright.stop()
        self.reward_model.save_model()
        print("Agent shutdown complete")

# Complete usage example
async def main():
    # Initialize agent with full setup
    agent = SelfLearningAgent()
    await agent.initialize_browser()
    
    try:
        # Example interaction sequence
        queries = [
            "What's the current weather in Tokyo?",
            "Find recent articles about AI advancements in healthcare",
            "Extract the main headline from https://www.bbc.com"
        ]
        
        for query in queries:
            print(f"\nProcessing: {query}")
            result = await agent.process_query(query)
            
            if result['success']:
                print(f"Response: {result['response'][:500]}...")
                print(f"Auto Reward: {result['reward']:.2f}")
                
                # Simulate user feedback (0-1 scale)
                feedback = 0.8 if "weather" in query else 0.7
                agent.integrate_feedback(query, feedback)
            else:
                print(f"Error: {result['error']}")
                
    finally:
        await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(main())