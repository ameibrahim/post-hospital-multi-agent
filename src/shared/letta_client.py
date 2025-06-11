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
        
        # Create enhanced memory blocks with patient information
        persona_block = CreateBlock(
            label="persona",
            value=f"""You are Prof.Dux, a caring and knowledgeable post-discharge healthcare assistant specifically assigned to {patient_data['name']}.

🩺 **Your Identity**: You are Prof.Dux, a dedicated healthcare AI assistant with extensive medical knowledge and a compassionate bedside manner, personally caring for {patient_data['name']}.

📋 **Your Patient**: {patient_data['name']} (Patient ID: {patient_data.get('patient_id', 'Not Set')})

📋 **Your Responsibilities**:
1. Support {patient_data['name']}'s recovery and wellness with personalized guidance
2. Monitor conversations for concerning symptoms and alert nurses when needed
3. Provide clear medication guidance specific to {patient_data['name']}'s prescriptions
4. Answer health questions with evidence-based information relevant to their conditions
5. Offer emotional support and encouragement during {patient_data['name']}'s recovery
6. Alert the nursing staff immediately if you detect urgent medical issues

💡 **Your Communication Style**:
- Always address {patient_data['name']} by name and introduce yourself as "Prof.Dux"
- Be warm, professional, and empathetic
- Reference their specific medical conditions and medications when relevant
- Provide specific, actionable advice based on their discharge plan
- Show genuine concern for {patient_data['name']}'s wellbeing

⚠️ **Important Guidelines**:
- If {patient_data['name']} reports severe symptoms, immediately recommend they contact their nurse
- Never provide emergency medical advice - direct them to call emergency services
- Always encourage {patient_data['name']} to follow their prescribed treatment plans
- Be encouraging but realistic about recovery expectations
- Remember their allergies when discussing any treatments or medications

Remember: You are {patient_data['name']}'s personal healthcare assistant, here to support, guide, and care for them during their recovery journey."""
        )
        
        # Create detailed patient information block
        medical_info = self._format_medications(patient_data.get('medications', []))
        patient_block = CreateBlock(
            label="human",  
            value=f"""PATIENT INFORMATION - ALWAYS REMEMBER THIS:

👤 **Patient Details**:
• Name: {patient_data['name']}
• Patient ID: {patient_data.get('patient_id', 'Not Set')}
• Email: {patient_data.get('email', 'Not provided')}

🏥 **Medical History**:
• Current Medical Conditions: {', '.join(patient_data.get('conditions', [])) or 'None listed'}
• Known Allergies: {', '.join(patient_data.get('allergies', [])) or 'None known'}

💊 **Current Medications**:
{medical_info}

📋 **Discharge Plan**:
{patient_data.get('discharge_plan', 'Standard follow-up care')}

🎯 **Care Instructions**: 
Always reference this patient information when providing care. Address {patient_data['name']} by name, consider their specific conditions and medications, and be aware of their allergies. This is {patient_data['name']}'s personalized healthcare assistant session."""
        )
        
        # Create agent using OpenAI models
        agent = self.client.agents.create(
            name=f"prof-dux-{patient_data['name'].lower().replace(' ', '-')}",
            memory_blocks=[persona_block, patient_block],
            model="openai/gpt-4o-mini",
            embedding="openai/text-embedding-3-small",
            context_window_limit=16000
        )
        
        # Send an initial system message to reinforce patient context
        try:
            initial_context = f"""SYSTEM CONTEXT: You are now active as Prof.Dux, the personal healthcare assistant for {patient_data['name']} (ID: {patient_data.get('patient_id', 'Not Set')}). 

Key patient information:
- Conditions: {', '.join(patient_data.get('conditions', [])) or 'None'}
- Medications: {len(patient_data.get('medications', []))} prescribed medications
- Allergies: {', '.join(patient_data.get('allergies', [])) or 'None known'}

When {patient_data['name']} messages you, greet them warmly by name and let them know you're here to help with their recovery. Always remember their specific medical information when providing guidance."""
            
            self.client.agents.messages.create(
                agent_id=agent.id,
                messages=[MessageCreate(role="system", content=initial_context)]
            )
            print(f"✅ Successfully initialized agent context for {patient_data['name']}")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not send initial context message: {e}")
        
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
            
            # Get agent memory to check if patient context is available
            try:
                agent = self.client.agents.get(agent_id)
                patient_name = "Unknown Patient"
                
                # Extract patient name from memory blocks
                if hasattr(agent, 'memory_blocks') and agent.memory_blocks:
                    for block in agent.memory_blocks:
                        if hasattr(block, 'value') and 'Patient Details' in str(block.value):
                            # Extract patient name from the memory block
                            import re
                            name_match = re.search(r'Name: ([^\n]+)', str(block.value))
                            if name_match:
                                patient_name = name_match.group(1).strip()
                                break
                
                # If this is a user message, enhance it with patient context reminder
                if role == "user" and patient_name != "Unknown Patient":
                    content = f"Patient {patient_name} says: {message}"
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not retrieve agent memory: {e}")
            
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
        """Get agent's memory blocks for debugging"""
        try:
            agent = self.client.agents.get(agent_id)
            memory_info = {
                "agent_name": getattr(agent, 'name', 'Unknown'),
                "memory_blocks": []
            }
            
            if hasattr(agent, 'memory_blocks') and agent.memory_blocks:
                for i, block in enumerate(agent.memory_blocks):
                    block_info = {
                        "index": i,
                        "label": getattr(block, 'label', 'unknown'),
                        "value": str(getattr(block, 'value', ''))[:200] + "..." if len(str(getattr(block, 'value', ''))) > 200 else str(getattr(block, 'value', ''))
                    }
                    memory_info["memory_blocks"].append(block_info)
            
            return memory_info
        except Exception as e:
            print(f"❌ Error getting agent memory: {e}")
            return {"error": str(e)}
    
    def refresh_patient_context(self, agent_id: str, patient_data: Dict) -> bool:
        """Refresh patient context in agent memory if needed"""
        try:
            # Send a context refresh message
            context_refresh = f"""CONTEXT REFRESH: Remember, you are Prof.Dux caring for {patient_data['name']} (ID: {patient_data.get('patient_id', 'Not Set')}).

Current patient details:
• Medical Conditions: {', '.join(patient_data.get('conditions', [])) or 'None listed'}
• Current Medications: {self._format_medications(patient_data.get('medications', []))}
• Known Allergies: {', '.join(patient_data.get('allergies', [])) or 'None known'}
• Discharge Plan: {patient_data.get('discharge_plan', 'Standard follow-up care')}

Always address {patient_data['name']} by name and reference their specific medical information when providing guidance."""
            
            self.client.agents.messages.create(
                agent_id=agent_id,
                messages=[MessageCreate(role="system", content=context_refresh)]
            )
            
            print(f"✅ Refreshed patient context for {patient_data['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Error refreshing patient context: {e}")
            return False
    
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
