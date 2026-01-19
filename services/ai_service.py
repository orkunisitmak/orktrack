"""AI Service for Gemini integration."""

import json
import re
from typing import Optional, Dict, Any, List, Generator
from datetime import datetime

import google.generativeai as genai

from config import settings
from utils.prompts import PromptTemplates
from database import DatabaseManager


class AIService:
    """Service class for AI-powered features using Google Gemini."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the AI service.
        
        Args:
            api_key: Gemini API key (uses settings if not provided)
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = settings.gemini_model
        self.model = None
        self._configure()
    
    def _configure(self):
        """Configure the Gemini API."""
        if not self.api_key:
            return
        
        genai.configure(api_key=self.api_key)
        
        # Configure generation settings
        generation_config = genai.GenerationConfig(
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
        )
        
        # Configure safety settings
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ]
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=generation_config,
            safety_settings=safety_settings,
            system_instruction=PromptTemplates.SYSTEM_PROMPT,
        )
    
    def is_configured(self) -> bool:
        """Check if the AI service is properly configured."""
        return self.model is not None and self.api_key is not None
    
    def chat(
        self,
        user_query: str,
        user_data: Dict[str, Any],
        recent_activities: List[Dict],
        health_summary: Dict[str, Any],
        chat_history: Optional[List[Dict]] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Process a chat query with fitness context.
        
        Args:
            user_query: The user's question
            user_data: User profile data
            recent_activities: List of recent activity dicts
            health_summary: Aggregated health metrics
            chat_history: Previous messages in the conversation
            session_id: Session ID for saving chat history
            
        Returns:
            AI response string
        """
        if not self.is_configured():
            return "AI service is not configured. Please add your Gemini API key to the .env file."
        
        # Build context-rich prompt
        prompt = PromptTemplates.chat_context_prompt(
            user_data=user_data,
            recent_activities=recent_activities,
            health_summary=health_summary,
            user_query=user_query
        )
        
        try:
            # Build conversation history
            history = []
            if chat_history:
                for msg in chat_history[-10:]:  # Last 10 messages for context
                    history.append({
                        "role": "user" if msg.get("role") == "user" else "model",
                        "parts": [msg.get("content", "")]
                    })
            
            # Start chat with history
            chat = self.model.start_chat(history=history)
            
            # Generate response
            response = chat.send_message(prompt)
            response_text = response.text
            
            # Save to database
            if session_id:
                DatabaseManager.save_chat_message(
                    session_id=session_id,
                    role="user",
                    content=user_query,
                    context_data={"health_summary": health_summary}
                )
                DatabaseManager.save_chat_message(
                    session_id=session_id,
                    role="assistant",
                    content=response_text
                )
            
            return response_text
            
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
    
    def chat_stream(
        self,
        user_query: str,
        user_data: Dict[str, Any],
        recent_activities: List[Dict],
        health_summary: Dict[str, Any],
        chat_history: Optional[List[Dict]] = None,
    ) -> Generator[str, None, None]:
        """
        Stream chat response for real-time display.
        
        Yields:
            Response text chunks
        """
        if not self.is_configured():
            yield "AI service is not configured. Please add your Gemini API key."
            return
        
        prompt = PromptTemplates.chat_context_prompt(
            user_data=user_data,
            recent_activities=recent_activities,
            health_summary=health_summary,
            user_query=user_query
        )
        
        try:
            history = []
            if chat_history:
                for msg in chat_history[-10:]:
                    history.append({
                        "role": "user" if msg.get("role") == "user" else "model",
                        "parts": [msg.get("content", "")]
                    })
            
            chat = self.model.start_chat(history=history)
            response = chat.send_message(prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            yield f"\n\nI apologize, but I encountered an error: {str(e)}"
    
    def generate_workout_plan(
        self,
        user_data: Dict[str, Any],
        fitness_goals: Dict[str, Any],
        recent_activities: List[Dict],
        health_metrics: Dict[str, Any],
        plan_duration: str = "week"
    ) -> Dict[str, Any]:
        """
        Generate a personalized workout plan.
        
        Args:
            user_data: User profile data
            fitness_goals: User's fitness goals
            recent_activities: Recent workout history
            health_metrics: Current health metrics
            plan_duration: "week" or "month"
            
        Returns:
            Workout plan dictionary
        """
        if not self.is_configured():
            return {"error": "AI service not configured"}
        
        prompt = PromptTemplates.workout_plan_prompt(
            user_data=user_data,
            fitness_goals=fitness_goals,
            recent_activities=recent_activities,
            health_metrics=health_metrics,
            plan_duration=plan_duration
        )
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Extract JSON from response
            plan_data = self._extract_json(response_text)
            
            if plan_data:
                plan_data["ai_model"] = self.model_name
                plan_data["generated_at"] = datetime.now().isoformat()
                plan_data["plan_type"] = plan_duration + "ly"
                
                # Save to database
                saved_plan = DatabaseManager.save_workout_plan(plan_data)
                plan_data["plan_id"] = saved_plan.id if saved_plan else None
                
                return plan_data
            else:
                return {
                    "error": "Failed to parse workout plan",
                    "raw_response": response_text
                }
                
        except Exception as e:
            return {"error": f"Failed to generate workout plan: {str(e)}"}
    
    def generate_health_insights(
        self,
        health_data: Dict[str, Any],
        trends: Dict[str, Any],
        activities: List[Dict],
        period: str = "week"
    ) -> Dict[str, Any]:
        """
        Generate AI-powered health insights.
        
        Args:
            health_data: Health metrics summary
            trends: Trend comparisons with previous period
            activities: Recent activities
            period: Analysis period ("week" or "month")
            
        Returns:
            Health insights dictionary
        """
        if not self.is_configured():
            return {"error": "AI service not configured"}
        
        prompt = PromptTemplates.health_insights_prompt(
            health_data=health_data,
            trends=trends,
            activities=activities,
            period=period
        )
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Extract JSON from response
            insights_data = self._extract_json(response_text)
            
            if insights_data:
                insights_data["ai_model"] = self.model_name
                insights_data["generated_at"] = datetime.now().isoformat()
                insights_data["period"] = period
                
                # Save to database
                insights_data["date"] = datetime.now().date().isoformat()
                DatabaseManager.save_health_insight(insights_data)
                
                return insights_data
            else:
                return {
                    "error": "Failed to parse health insights",
                    "raw_response": response_text
                }
                
        except Exception as e:
            return {"error": f"Failed to generate health insights: {str(e)}"}
    
    def recommend_goals(
        self,
        current_metrics: Dict[str, Any],
        activity_history: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate personalized goal recommendations.
        
        Args:
            current_metrics: Current fitness metrics
            activity_history: Historical activity data
            
        Returns:
            Goal recommendations dictionary
        """
        if not self.is_configured():
            return {"error": "AI service not configured"}
        
        prompt = PromptTemplates.goal_recommendation_prompt(
            current_metrics=current_metrics,
            activity_history=activity_history
        )
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            goals_data = self._extract_json(response_text)
            
            if goals_data:
                return goals_data
            else:
                return {
                    "error": "Failed to parse goal recommendations",
                    "raw_response": response_text
                }
                
        except Exception as e:
            return {"error": f"Failed to generate goals: {str(e)}"}
    
    def analyze_activity(
        self,
        activity_data: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> str:
        """
        Analyze a specific activity and provide feedback.
        
        Args:
            activity_data: Activity details
            user_profile: User profile for context
            
        Returns:
            Analysis text
        """
        if not self.is_configured():
            return "AI service not configured."
        
        prompt = f"""
Analyze this workout and provide brief, actionable feedback:

**Activity Type:** {activity_data.get('activityType', {}).get('typeKey', 'Unknown')}
**Duration:** {activity_data.get('duration', 0) / 60:.0f} minutes
**Distance:** {activity_data.get('distance', 0) / 1000:.2f} km
**Calories:** {activity_data.get('calories', 0)}
**Average HR:** {activity_data.get('averageHR', 'N/A')} bpm
**Max HR:** {activity_data.get('maxHR', 'N/A')} bpm
**Elevation Gain:** {activity_data.get('elevationGain', 0):.0f} m

Provide:
1. A brief performance summary (2-3 sentences)
2. One thing done well
3. One area for improvement
4. Recovery recommendation

Keep the response concise and encouraging.
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Unable to analyze activity: {str(e)}"
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from AI response text."""
        # Try to find JSON block in markdown code fence
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                json_str = json_match.group(0)
            else:
                return None
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to fix common JSON issues
            json_str = json_str.replace("'", '"')
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return None
    
    def quick_answer(self, question: str, context: str = "") -> str:
        """
        Get a quick answer without full context building.
        
        Args:
            question: User's question
            context: Optional additional context
            
        Returns:
            Response text
        """
        if not self.is_configured():
            return "AI service not configured."
        
        prompt = f"""
{context}

Question: {question}

Provide a helpful, concise answer. If the question is about health or fitness, include relevant tips.
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Unable to process question: {str(e)}"
