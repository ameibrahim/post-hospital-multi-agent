import os
from typing import Dict, List, Optional
from letta_client import Letta, CreateBlock, MessageCreate

class LettaClient:
    def __init__(self, server_url: str = None):
        self.server_url = server_url or os.getenv('LETTA_SERVER_URL', 'http://localhost:8283')
        # Initialize the new Letta client
        self.client = Letta(base_url=self.server_url)
    
    def create_patient_agent(self, patient_data: Dict) -> str:
        """Create a patient agent with medical history using the new Letta API with OpenAI"""
        
        # Create memory blocks using the new CreateBlock format
        memory_blocks = [
            CreateBlock(
                label="persona",
                value="""You are Prof.Dux, a caring and knowledgeable post-discharge healthcare assistant. Your role is to:

🩺 **Your Identity**: You are Prof.Dux, a dedicated healthcare AI assistant with extensive medical knowledge and a compassionate bedside manner.

📋 **Your Responsibilities**:
1. Support patient recovery and wellness with personalized guidance
2. Monitor conversations for concerning symptoms and alert nurses when needed
3. Provide clear, accurate medication guidance and scheduling
4. Answer health questions with evidence-based information
5. Offer emotional support and encouragement during recovery
6. Alert the nursing staff immediately if you detect urgent medical issues

💡 **Your Communication Style**:
- Always introduce yourself as "Prof.Dux" on first contact
- Be warm, professional, and empathetic
- Use clear, simple language that patients can understand
- Provide specific, actionable advice when possible
- Show genuine concern for the patient's wellbeing

⚠️ **Important Guidelines**:
- If a patient reports severe symptoms, immediately recommend they contact their nurse
- Never provide emergency medical advice - direct patients to call emergency services
- Always encourage patients to follow their prescribed treatment plans
- Be encouraging but realistic about recovery expectations

Remember: You are here to support, guide, and care for patients during their recovery journey."""
            ),
            CreateBlock(
                label="human",  
                value=f"""Patient: {patient_data['name']} (ID: {patient_data.get('patient_id', 'Not Set')})

📋 **Medical Profile**:
• Medical Conditions: {', '.join(patient_data.get('conditions', [])) or 'None listed'}
• Current Medications: {self._format_medications(patient_data.get('medications', []))}
• Known Allergies: {', '.join(patient_data.get('allergies', [])) or 'None known'}
• Discharge Plan: {patient_data.get('discharge_plan', 'Standard follow-up care')}

🎯 **Care Focus**: Provide personalized support based on this patient's specific medical needs, medications, and recovery plan. Always consider their conditions and allergies when giving advice."""
            )
        ]
        
        # Create agent using OpenAI models instead of Gemini
        agent = self.client.agents.create(
            name=f"prof-dux-{patient_data['name'].lower().replace(' ', '-')}",
            memory_blocks=memory_blocks,
            model="openai/gpt-4o-mini",  # Changed from Gemini to OpenAI
            embedding="openai/text-embedding-3-small",  # Changed from Gemini to OpenAI
            context_window_limit=16000  # Added context window limit as shown in docs
        )
        
        return agent.id
    
    def send_message(self, agent_id: str, message: str) -> Dict:
        """Send message to agent and get response using new API"""
        try:
            # Determine message role - if it's a nurse instruction, send as system message
            if message.startswith('📋 **CARE INSTRUCTION FROM NURSE:**'):
                role = "system"
                content = message
            else:
                role = "user"
                content = message
            
            response = self.client.agents.messages.create(
                agent_id=agent_id,
                messages=[
                    MessageCreate(
                        role=role,
                        content=content
                    )
                ]
            )
            
            # Convert response to JSON-serializable format
            serializable_messages = []
            if hasattr(response, 'messages') and response.messages:
                for msg in response.messages:
                    try:
                        # Extract message info based on the new API structure
                        content_text = ''
                        if hasattr(msg, 'content') and msg.content:
                            content_text = str(msg.content)
                        elif hasattr(msg, 'reasoning') and msg.reasoning:
                            content_text = str(msg.reasoning)
                        
                        msg_data = {
                            'id': getattr(msg, 'id', ''),
                            'message_type': getattr(msg, 'message_type', 'unknown'),
                            'content': content_text,
                            'date': str(getattr(msg, 'created_at', ''))
                        }
                        serializable_messages.append(msg_data)
                    except Exception as e:
                        print(f"⚠️  Warning: Could not serialize message: {e}")
                        continue
            
            return {
                "messages": serializable_messages,
                "success": True,
                "message_count": len(serializable_messages)
            }
        except Exception as e:
            raise Exception(f"Failed to send message: {str(e)}")
    
    def get_agent_memory(self, agent_id: str) -> Dict:
        """Get agent's memory blocks"""
        try:
            agent = self.client.agents.get(agent_id)
            return {"memory_blocks": agent.memory_blocks if hasattr(agent, 'memory_blocks') else []}
        except Exception as e:
            return {}
    
    def list_agents(self) -> List[Dict]:
        """List all agents"""
        try:
            agents = self.client.agents.list()
            # Handle both paginated and direct list responses
            agents_list = agents.data if hasattr(agents, 'data') else agents
            return [{"id": agent.id, "name": agent.name} for agent in agents_list]
        except Exception as e:
            return []
    
    def get_agent_messages(self, agent_id: str, limit: int = 10) -> List[Dict]:
        """Get recent messages for agent"""
        try:
            messages = self.client.agents.messages.list(agent_id, limit=limit)
            serializable_messages = []
            
            messages_list = messages.data if hasattr(messages, 'data') else messages
            for msg in messages_list:
                try:
                    msg_data = {
                        'message_type': getattr(msg, 'message_type', 'unknown'),
                        'content': getattr(msg, 'content', '') or str(getattr(msg, 'reasoning', '')),
                        'date': str(getattr(msg, 'created_at', ''))
                    }
                    serializable_messages.append(msg_data)
                except Exception as e:
                    print(f"⚠️  Warning: Could not serialize message: {e}")
                    continue
                    
            return serializable_messages
        except Exception as e:
            return []
    
    def _format_medications(self, medications: List[Dict]) -> str:
        """Format medications list for memory"""
        if not medications:
            return "None prescribed"
        return '\n'.join([f"  • {med['name']}: {med['dosage']} {med['frequency']}" 
                         for med in medications])