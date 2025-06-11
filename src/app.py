from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging for production
if os.getenv('FLASK_ENV') == 'production':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        handlers=[
            logging.FileHandler('/app/logs/app.log'),
            logging.StreamHandler()
        ]
    )
else:
    logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Production security settings
if os.getenv('FLASK_ENV') == 'production':
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
    )

# Initialize clients
try:
    from shared.letta_client import LettaClient
    from shared.models import Patient, Medication, SimpleStorage
    from shared.email_service import EmailService
    
    letta_client = LettaClient()
    storage = SimpleStorage(filename='/app/data/data.json')  # Persistent storage location
    email_service = EmailService()
    
    app.logger.info("✅ System initialized successfully")
except Exception as e:
    app.logger.error(f"❌ Error initializing clients: {e}")
    import traceback
    app.logger.error(f"❌ Traceback: {traceback.format_exc()}")
    letta_client = None
    storage = None
    email_service = None

# Create data directory if it doesn't exist
os.makedirs('/app/data', exist_ok=True)
os.makedirs('/app/logs', exist_ok=True)

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check if core services are available
        health_status = {
            'status': 'healthy',
            'letta_client': bool(letta_client),
            'storage': bool(storage),
            'email_service': bool(email_service and email_service.api_instance),
            'timestamp': str(datetime.datetime.now())
        }
        
        if all([letta_client, storage, email_service]):
            return jsonify(health_status), 200
        else:
            health_status['status'] = 'degraded'
            return jsonify(health_status), 200
            
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': str(datetime.datetime.now())
        }), 500

@app.route('/')
def index():
    """Home page with dynamic login options"""
    current_user = None
    patients_for_login = []
    
    if storage:
        patients_for_login = storage.get_patients_for_login()
    
    if 'role' in session:
        if session['role'] == 'nurse':
            current_user = {'role': 'nurse'}
        elif session['role'] == 'patient' and 'patient_id' in session:
            patient = storage.get_patient_by_id(session['patient_id']) if storage else None
            if patient:
                current_user = {
                    'role': 'patient', 
                    'name': patient.name, 
                    'patient_id': session['patient_id']
                }
    
    return render_template('login.html', 
                         current_user=current_user, 
                         patients=patients_for_login)

@app.route('/login', methods=['POST'])
def login():
    """Handle login requests"""
    role = request.form.get('role')
    
    if role == 'nurse':
        session['role'] = 'nurse'
        app.logger.info("Nurse logged in")
        return redirect(url_for('nurse_dashboard'))
    elif role == 'patient':
        patient_id = request.form.get('patient_id')
        if patient_id and storage:
            patient = storage.get_patient_by_id(patient_id)
            if patient and patient.agent_id:
                session['role'] = 'patient'
                session['patient_id'] = patient_id
                app.logger.info(f"Patient {patient.name} logged in")
                return redirect(url_for('patient_dashboard', patient_id=patient_id))
        return redirect(url_for('index'))
    
    return redirect(url_for('index'))

@app.route('/patient-login', methods=['POST'])
def patient_login():
    """Handle patient login with credentials"""
    patient_id = request.form.get('patient_id')
    password = request.form.get('password')
    
    if not patient_id or not password:
        return redirect(url_for('index'))
    
    if storage:
        # Authenticate patient
        patient = storage.authenticate_patient(patient_id, password)
        if patient and patient.agent_id:
            session['role'] = 'patient'
            session['patient_id'] = patient_id
            app.logger.info(f"Patient {patient.name} authenticated with credentials")
            return redirect(url_for('patient_dashboard', patient_id=patient_id))
    
    app.logger.warning(f"Failed authentication attempt for patient ID: {patient_id}")
    return redirect(url_for('index'))

@app.route('/magic-login', methods=['GET', 'POST'])
def magic_login():
    """Handle magic link login"""
    if request.method == 'GET':
        # Handle magic link from email
        token = request.args.get('token')
        if token and storage:
            patient = storage.get_patient_by_token(token)
            if patient:
                session['role'] = 'patient'
                session['patient_id'] = patient.patient_id
                app.logger.info(f"Patient {patient.name} authenticated with magic link")
                return redirect(url_for('patient_dashboard', patient_id=patient.patient_id))
        return redirect(url_for('index'))
    
    elif request.method == 'POST':
        # Handle manual token entry
        token = request.form.get('token')
        if token and storage:
            patient = storage.get_patient_by_token(token)
            if patient:
                session['role'] = 'patient'
                session['patient_id'] = patient.patient_id
                app.logger.info(f"Patient {patient.name} authenticated with manual token")
                return redirect(url_for('patient_dashboard', patient_id=patient.patient_id))
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Clear session and return to login"""
    app.logger.info("User logged out")
    session.clear()
    return redirect(url_for('index'))

# NURSE ROUTES
@app.route('/nurse')
def nurse_dashboard():
    """Nurse dashboard with patient management"""
    if session.get('role') != 'nurse':
        return redirect(url_for('index'))
    
    if not storage:
        return jsonify({"error": "Storage not initialized"}), 500
        
    patients = storage.get_patients()
    alerts = storage.get_alerts()
    stats = storage.get_statistics()
    
    return render_template('nurse.html', 
                         patients=patients, 
                         alerts=alerts,
                         stats=stats)

@app.route('/api/create_patient', methods=['POST'])
def create_patient():
    """Create a new patient with AI agent and send credentials"""
    if session.get('role') != 'nurse':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not letta_client or not storage or not email_service:
        return jsonify({'error': 'System not initialized'}), 500
    
    data = request.json
    
    # Validate required fields
    if not data.get('name') or not data.get('patient_id') or not data.get('email'):
        return jsonify({'error': 'Patient name, ID, and email are required'}), 400
    
    # Validate patient ID uniqueness
    if not storage.validate_patient_id(data['patient_id']):
        return jsonify({'error': 'Patient ID already exists or is invalid'}), 400
    
    # Validate email uniqueness
    if not storage.validate_email(data['email']):
        return jsonify({'error': 'Email address already exists'}), 400
    
    # Create medications list
    medications = []
    for med in data.get('medications', []):
        if med.get('name') and med.get('dosage') and med.get('frequency'):
            medications.append(Medication(
                name=med['name'],
                dosage=med['dosage'], 
                frequency=med['frequency']
            ))
    
    # Create patient
    patient = Patient(
        name=data['name'],
        email=data['email'],
        patient_id=data['patient_id'],
        conditions=data.get('conditions', []),
        medications=medications,
        allergies=data.get('allergies', []),
        discharge_plan=data.get('discharge_plan', '')
    )
    
    try:
        # Generate password and magic token
        password = patient.generate_password()
        magic_token = patient.generate_magic_token()
        
        # Create Letta agent
        try:
            agent_id = letta_client.create_patient_agent(patient.to_dict())
            patient.agent_id = agent_id
            app.logger.info(f"✅ Created Letta agent {agent_id} for {patient.name}")
        except Exception as letta_error:
            app.logger.warning(f"⚠️ Warning: Could not create Letta agent: {letta_error}")
            # Continue without Letta agent for now
            patient.agent_id = None
        
        # Store patient (even if Letta agent creation failed)
        storage.add_patient(patient)
        
        # Send credentials email using email service
        email_sent = False
        try:
            email_sent = email_service.send_patient_credentials_email(
                patient.to_dict(), 
                password, 
                magic_token, 
                request.host_url
            )
        except Exception as email_error:
            app.logger.warning(f"⚠️ Warning: Could not send email: {email_error}")
        
        app.logger.info(f"✅ Created patient {patient.name} (Agent: {'✅' if patient.agent_id else '❌'}, Email: {'✅' if email_sent else '❌'})")
        
        return jsonify({
            'success': True, 
            'agent_id': patient.agent_id,
            'email_sent': email_sent,
            'password': password,
            'magic_token': magic_token,
            'warnings': {
                'letta_agent': not bool(patient.agent_id),
                'email_delivery': not email_sent
            }
        })
        
    except ValueError as e:
        app.logger.error(f"Validation error creating patient: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        import traceback
        app.logger.error(f"❌ Error creating patient: {e}")
        app.logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

@app.route('/api/delete_patient', methods=['DELETE'])
def delete_patient():
    """Delete a patient and their AI agent"""
    if session.get('role') != 'nurse':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not storage:
        return jsonify({'error': 'System not initialized'}), 500
    
    data = request.json
    patient_name = data.get('patient_name')
    
    if not patient_name:
        return jsonify({'error': 'Patient name is required'}), 400
    
    try:
        # Get patient info before deletion
        patient = storage.get_patient_by_name(patient_name)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Delete from Letta (if agent exists)
        if patient.agent_id and letta_client:
            try:
                # Note: Letta client may not have a direct delete method
                # This depends on the Letta API - you may need to implement this
                # For now, we'll just remove from our storage
                app.logger.info(f"🗑️ Would delete Letta agent {patient.agent_id} for {patient_name}")
            except Exception as e:
                app.logger.warning(f"⚠️ Warning: Could not delete Letta agent {patient.agent_id}: {e}")
        
        # Delete from our storage
        success = storage.delete_patient(patient_name)
        
        if success:
            app.logger.info(f"✅ Deleted patient {patient_name}")
            return jsonify({'success': True, 'message': f'Patient {patient_name} deleted successfully'})
        else:
            return jsonify({'error': 'Patient not found'}), 404
            
    except Exception as e:
        app.logger.error(f"❌ Error deleting patient: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/send_instruction', methods=['POST'])
def send_instruction():
    """Send care instruction from nurse to patient"""
    if session.get('role') != 'nurse':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not letta_client or not storage:
        return jsonify({'error': 'System not initialized'}), 500
    
    data = request.json
    patient_name = data.get('patient_name')
    instruction = data.get('instruction')
    
    if not patient_name or not instruction:
        return jsonify({'error': 'Patient name and instruction are required'}), 400
    
    patient = storage.get_patient_by_name(patient_name)
    if not patient or not patient.agent_id:
        return jsonify({'error': 'Patient or agent not found'}), 404
    
    try:
        # Send instruction to the agent as a system message
        nurse_message = f"📋 **CARE INSTRUCTION FROM NURSE:** {instruction}"
        response = letta_client.send_message(patient.agent_id, nurse_message)
        
        # Store the instruction
        storage.add_nurse_instruction(patient_name, instruction)
        
        app.logger.info(f"✅ Sent instruction to {patient_name}: {instruction}")
        return jsonify({'success': True, 'response': response})
        
    except Exception as e:
        app.logger.error(f"❌ Error sending instruction: {e}")
        return jsonify({'error': str(e)}), 500

# PATIENT ROUTES
@app.route('/patient/<patient_id>')
def patient_dashboard(patient_id):
    """Patient dashboard with chat interface"""
    if session.get('role') != 'patient' or session.get('patient_id') != patient_id:
        return redirect(url_for('index'))
    
    if not storage:
        return jsonify({"error": "Storage not initialized"}), 500
    
    patient = storage.get_patient_by_id(patient_id)
    if not patient:
        return redirect(url_for('index'))
    
    messages = []
    if patient.agent_id and letta_client:
        try:
            raw_messages = letta_client.get_agent_messages(patient.agent_id, limit=20)
            messages = _format_messages_for_display(raw_messages)
        except Exception as e:
            app.logger.error(f"❌ Error loading messages for {patient.name}: {e}")
    
    return render_template('patient.html', 
                         patient=patient, 
                         patient_name=patient.name,
                         messages=messages,
                         patient_id=patient_id)

@app.route('/api/send_message', methods=['POST'])
def send_message():
    """Send message from patient to their AI agent"""
    if session.get('role') != 'patient':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not letta_client or not storage:
        return jsonify({'error': 'System not initialized'}), 500
    
    data = request.json
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    patient_id = session.get('patient_id')
    patient = storage.get_patient_by_id(patient_id)
    
    if not patient or not patient.agent_id:
        return jsonify({'error': 'Patient agent not found'}), 404
    
    try:
        app.logger.info(f"🔍 Sending message from {patient.name}: {message}")
        
        # Check if this is the first message - if so, refresh context
        try:
            recent_messages = letta_client.get_agent_messages(patient.agent_id, limit=5)
            if len(recent_messages) < 2:  # Only system messages exist
                app.logger.info(f"🔄 Refreshing patient context for {patient.name}")
                letta_client.refresh_patient_context(patient.agent_id, patient.to_dict())
        except Exception as e:
            app.logger.warning(f"⚠️ Could not check/refresh context: {e}")
        
        response = letta_client.send_message(patient.agent_id, message)
        
        # Enhanced alert detection
        _check_for_alerts(patient.name, message, storage)
        
        # Filter response for clean display
        clean_response = _filter_agent_response(response)
        
        app.logger.info(f"✅ Response sent to {patient.name}")
        return jsonify({'success': True, 'response': clean_response})
        
    except Exception as e:
        app.logger.error(f"❌ Error in send_message for {patient.name}: {e}")
        import traceback
        app.logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

# Add debugging endpoints for development
@app.route('/api/debug/agent_memory/<patient_name>', methods=['GET'])
def debug_agent_memory(patient_name):
    """Debug endpoint to check agent memory (development only)"""
    if session.get('role') != 'nurse':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not letta_client or not storage:
        return jsonify({'error': 'System not initialized'}), 500
    
    patient = storage.get_patient_by_name(patient_name)
    if not patient or not patient.agent_id:
        return jsonify({'error': 'Patient or agent not found'}), 404
    
    try:
        memory_info = letta_client.get_agent_memory(patient.agent_id)
        return jsonify({
            'success': True,
            'patient_name': patient_name,
            'agent_id': patient.agent_id,
            'memory_info': memory_info
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh_patient_context/<patient_name>', methods=['POST'])
def refresh_patient_context(patient_name):
    """Refresh patient context in agent memory"""
    if session.get('role') != 'nurse':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not letta_client or not storage:
        return jsonify({'error': 'System not initialized'}), 500
    
    patient = storage.get_patient_by_name(patient_name)
    if not patient or not patient.agent_id:
        return jsonify({'error': 'Patient or agent not found'}), 404
    
    try:
        success = letta_client.refresh_patient_context(patient.agent_id, patient.to_dict())
        if success:
            return jsonify({'success': True, 'message': f'Context refreshed for {patient_name}'})
        else:
            return jsonify({'error': 'Failed to refresh context'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# UTILITY FUNCTIONS
def _format_messages_for_display(raw_messages):
    """Format messages for clean display in patient chat"""
    formatted_messages = []
    
    for msg in raw_messages:
        msg_type = msg.get('message_type', '')
        content = msg.get('content', '')
        
        # Skip internal messages
        if (msg_type == 'reasoning_message' or 
            not content or 
            content.strip() == '' or
            'More human than human is our motto' in content or
            content.strip().startswith('{') and 'type' in content):
            continue
        
        # Handle nurse instructions
        if content.startswith('📋 **CARE INSTRUCTION FROM NURSE:**'):
            formatted_messages.append({
                'role': 'system',
                'text': content.replace('📋 **CARE INSTRUCTION FROM NURSE:** ', 'Nurse: ')
            })
        # Handle user messages
        elif msg_type == 'user_message':
            clean_text = content.replace('**You:**', '').strip()
            if not clean_text.startswith('{'):  # Skip JSON messages
                formatted_messages.append({'role': 'user', 'text': clean_text})
        # Handle assistant messages
        elif (msg_type == 'assistant_message' and 
              not any(skip_phrase in content.lower() for skip_phrase in [
                  'core memory', 'archival memory', 'system_alert', 'i should'
              ])):
            clean_text = content.replace('**Assistant:**', '').strip()
            if clean_text and len(clean_text) > 10:
                formatted_messages.append({'role': 'assistant', 'text': clean_text})
    
    return formatted_messages

def _filter_agent_response(response):
    """Filter agent response for clean display"""
    clean_response = {"messages": [], "success": True, "message_count": 0}
    
    if response.get('messages'):
        for msg in response['messages']:
            msg_type = msg.get('message_type', '')
            content = msg.get('content', '')
            
            # Only include clean assistant messages
            if (msg_type == 'assistant_message' and 
                content and 
                not any(skip_phrase in content.lower() for skip_phrase in [
                    'core memory', 'archival memory', 'system_alert', 'no need to',
                    'i can answer using', 'i should'
                ]) and
                not content.strip().startswith('{')):
                clean_response['messages'].append(msg)
                clean_response['message_count'] += 1
    
    return clean_response

def _check_for_alerts(patient_name, message, storage):
    """Check message for alert conditions and create alerts if needed"""
    alert_keywords = [
        'inform the nurse', 'tell the nurse', 'contact the nurse', 
        'notify the nurse', 'alert the nurse', 'let the nurse know'
    ]
    
    urgent_keywords = [
        'chest pain', 'can\'t breathe', 'difficulty breathing', 'severe pain', 
        'emergency', 'help', 'dizzy', 'lightheaded', 'nausea', 'vomiting',
        'feel bad', 'feel terrible', 'feel awful', 'pain', 'hurt'
    ]
    
    message_lower = message.lower()
    
    if any(keyword in message_lower for keyword in alert_keywords):
        storage.add_alert(patient_name, f"Patient requested nurse contact: {message}", 'high')
    elif any(keyword in message_lower for keyword in urgent_keywords):
        storage.add_alert(patient_name, f"Concerning symptoms reported: {message}", 'medium')

# API Routes for system management
@app.route('/api/system/stats', methods=['GET'])
def get_system_stats():
    """Get system statistics"""
    if session.get('role') != 'nurse':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not storage:
        return jsonify({'error': 'System not initialized'}), 500
    
    return jsonify(storage.get_statistics())

@app.route('/api/alerts/clear', methods=['POST'])
def clear_alerts():
    """Clear all alerts"""
    if session.get('role') != 'nurse':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not storage:
        return jsonify({'error': 'System not initialized'}), 500
    
    storage.clear_alerts()
    return jsonify({'success': True})

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    import datetime
    app.logger.info("🏥 Starting Enhanced Post-Hospital Care System...")
    app.logger.info(f"🔧 Letta client: {'✅ Ready' if letta_client else '❌ Not available'}")
    app.logger.info(f"💾 Storage: {'✅ Ready' if storage else '❌ Not available'}")
    app.logger.info(f"📧 Email service: {'✅ Ready' if email_service and email_service.api_instance else '❌ Not available'}")
    
    if storage:
        stats = storage.get_statistics()
        app.logger.info(f"📊 System stats: {stats['total_patients']} patients, {stats['active_agents']} active agents")
    
    # Production vs Development
    if os.getenv('FLASK_ENV') == 'production':
        app.run(host='0.0.0.0', port=5011, debug=False)
    else:
        app.run(host='0.0.0.0', port=5011, debug=True)
