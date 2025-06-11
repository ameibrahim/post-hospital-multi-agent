from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import datetime
import os
import secrets
import string

@dataclass
class Medication:
    name: str
    dosage: str
    frequency: str

@dataclass 
class Patient:
    name: str
    email: str  # New field for patient email
    conditions: List[str]
    medications: List[Medication]
    allergies: List[str]
    discharge_plan: str
    patient_id: str = None
    agent_id: Optional[str] = None
    password: Optional[str] = None  # Generated password
    magic_token: Optional[str] = None  # Magic link token
    token_expires: Optional[str] = None  # Token expiration
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'email': self.email,
            'patient_id': self.patient_id,
            'conditions': self.conditions,
            'medications': [{'name': m.name, 'dosage': m.dosage, 'frequency': m.frequency} 
                          for m in self.medications],
            'allergies': self.allergies,
            'discharge_plan': self.discharge_plan,
            'agent_id': self.agent_id,
            'password': self.password,
            'magic_token': self.magic_token,
            'token_expires': self.token_expires
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Patient':
        medications = [Medication(**med) for med in data.get('medications', [])]
        return cls(
            name=data['name'],
            email=data.get('email', ''),
            patient_id=data.get('patient_id'),
            conditions=data.get('conditions', []),
            medications=medications,
            allergies=data.get('allergies', []),
            discharge_plan=data.get('discharge_plan', ''),
            agent_id=data.get('agent_id'),
            password=data.get('password'),
            magic_token=data.get('magic_token'),
            token_expires=data.get('token_expires')
        )
    
    def generate_password(self) -> str:
        """Generate a secure random password"""
        length = 12
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(characters) for _ in range(length))
        self.password = password
        return password
    
    def generate_magic_token(self) -> str:
        """Generate a magic link token that expires in 7 days"""
        token = secrets.token_urlsafe(32)
        expires = datetime.datetime.now() + datetime.timedelta(days=7)
        self.magic_token = token
        self.token_expires = expires.isoformat()
        return token
    
    def is_token_valid(self) -> bool:
        """Check if magic token is still valid"""
        if not self.magic_token or not self.token_expires:
            return False
        expiry = datetime.datetime.fromisoformat(self.token_expires)
        return datetime.datetime.now() < expiry

class SimpleStorage:
    """Simple file-based storage for demo purposes"""
    
    def __init__(self, filename: str = 'data.json'):
        self.filename = filename
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'patients': [], 
                'alerts': [],
                'nurse_instructions': []
            }
    
    def _save_data(self):
        with open(self.filename, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def add_patient(self, patient: Patient):
        """Add a new patient to storage"""
        # Check if patient ID already exists
        existing_ids = [p.get('patient_id') for p in self.data['patients']]
        if patient.patient_id in existing_ids:
            raise ValueError(f"Patient ID '{patient.patient_id}' already exists")
        
        # Check if patient name already exists
        existing_names = [p.get('name') for p in self.data['patients']]
        if patient.name in existing_names:
            raise ValueError(f"Patient name '{patient.name}' already exists")
        
        # Check if email already exists
        existing_emails = [p.get('email') for p in self.data['patients']]
        if patient.email in existing_emails:
            raise ValueError(f"Email '{patient.email}' already exists")
        
        self.data['patients'].append(patient.to_dict())
        self._save_data()
    
    def get_patients(self) -> List[Patient]:
        """Get all patients"""
        return [Patient.from_dict(p) for p in self.data['patients']]
    
    def get_patient_by_name(self, name: str) -> Optional[Patient]:
        """Get patient by name"""
        for p_data in self.data['patients']:
            if p_data['name'] == name:
                return Patient.from_dict(p_data)
        return None
    
    def get_patient_by_id(self, patient_id: str) -> Optional[Patient]:
        """Get patient by patient ID"""
        for p_data in self.data['patients']:
            if p_data.get('patient_id') == patient_id:
                return Patient.from_dict(p_data)
        return None
    
    def get_patient_by_token(self, token: str) -> Optional[Patient]:
        """Get patient by magic token"""
        for p_data in self.data['patients']:
            if p_data.get('magic_token') == token:
                patient = Patient.from_dict(p_data)
                if patient.is_token_valid():
                    return patient
        return None
    
    def authenticate_patient(self, patient_id: str, password: str) -> Optional[Patient]:
        """Authenticate patient with Patient ID and password"""
        for p_data in self.data['patients']:
            if (p_data.get('patient_id') == patient_id and 
                p_data.get('password') == password):
                return Patient.from_dict(p_data)
        return None
    
    def get_patient_credentials(self, patient_name: str) -> Optional[Dict[str, str]]:
        """Get patient credentials by name"""
        for p_data in self.data['patients']:
            if p_data['name'] == patient_name:
                return {
                    'patient_id': p_data.get('patient_id'),
                    'password': p_data.get('password'),
                    'magic_token': p_data.get('magic_token')
                }
        return None
    
    def update_patient_credentials(self, patient_name: str, password: str = None, magic_token: str = None):
        """Update patient credentials"""
        for p_data in self.data['patients']:
            if p_data['name'] == patient_name:
                if password:
                    p_data['password'] = password
                if magic_token:
                    p_data['magic_token'] = magic_token
                break
        self._save_data()
        """Get patient by magic token"""
        for p_data in self.data['patients']:
            if p_data.get('magic_token') == token:
                patient = Patient.from_dict(p_data)
                if patient.is_token_valid():
                    return patient
        return None
    
    def update_patient(self, patient: Patient):
        """Update existing patient data"""
        for i, p_data in enumerate(self.data['patients']):
            if p_data['name'] == patient.name:
                self.data['patients'][i] = patient.to_dict()
                self._save_data()
                break
    
    def delete_patient(self, patient_name: str) -> bool:
        """Delete a patient and all associated data"""
        # Find and remove the patient
        initial_count = len(self.data['patients'])
        self.data['patients'] = [p for p in self.data['patients'] if p['name'] != patient_name]
        
        if len(self.data['patients']) == initial_count:
            return False  # Patient not found
        
        # Remove associated alerts
        self.data['alerts'] = [a for a in self.data['alerts'] if a.get('patient_name') != patient_name]
        
        # Remove associated nurse instructions
        if 'nurse_instructions' in self.data:
            self.data['nurse_instructions'] = [
                inst for inst in self.data['nurse_instructions'] 
                if inst.get('patient_name') != patient_name
            ]
        
        self._save_data()
        return True
    
    def update_patient_agent_id(self, name: str, agent_id: str):
        """Update patient's agent ID"""
        for p in self.data['patients']:
            if p['name'] == name:
                p['agent_id'] = agent_id
                break
        self._save_data()
    
    def get_patients_for_login(self) -> List[Dict]:
        """Get simplified patient list for login page"""
        patients = []
        for p_data in self.data['patients']:
            if p_data.get('agent_id'):  # Only include patients with active agents
                patients.append({
                    'name': p_data['name'],
                    'patient_id': p_data.get('patient_id', 'Unknown')
                })
        return patients
    
    def add_alert(self, patient_name: str, message: str, priority: str = 'medium'):
        """Add an alert for a patient"""
        alert = {
            'patient_name': patient_name,
            'message': message,
            'priority': priority,
            'timestamp': datetime.datetime.now().isoformat()
        }
        self.data['alerts'].append(alert)
        self._save_data()
    
    def get_alerts(self) -> List[Dict]:
        """Get all alerts"""
        return self.data.get('alerts', [])
    
    def clear_alerts(self):
        """Clear all alerts"""
        self.data['alerts'] = []
        self._save_data()
    
    def remove_alert(self, index: int):
        """Remove a specific alert by index"""
        if 0 <= index < len(self.data['alerts']):
            del self.data['alerts'][index]
            self._save_data()
    
    def add_nurse_instruction(self, patient_name: str, instruction: str):
        """Store nurse instructions for patients"""
        nurse_instruction = {
            'patient_name': patient_name,
            'instruction': instruction,
            'timestamp': datetime.datetime.now().isoformat()
        }
        if 'nurse_instructions' not in self.data:
            self.data['nurse_instructions'] = []
        self.data['nurse_instructions'].append(nurse_instruction)
        self._save_data()
    
    def get_nurse_instructions(self, patient_name: str) -> List[Dict]:
        """Get nurse instructions for a specific patient"""
        if 'nurse_instructions' not in self.data:
            return []
        return [inst for inst in self.data['nurse_instructions'] 
                if inst['patient_name'] == patient_name]
    
    def validate_patient_id(self, patient_id: str) -> bool:
        """Validate that patient ID is unique and properly formatted"""
        if not patient_id or not patient_id.strip():
            return False
        
        # Check if ID already exists
        existing_ids = [p.get('patient_id') for p in self.data['patients']]
        return patient_id not in existing_ids
    
    def validate_email(self, email: str) -> bool:
        """Validate that email is unique"""
        if not email or not email.strip():
            return False
        
        # Check if email already exists
        existing_emails = [p.get('email') for p in self.data['patients']]
        return email not in existing_emails
    
    def get_statistics(self) -> Dict:
        """Get system statistics"""
        return {
            'total_patients': len(self.data['patients']),
            'active_agents': len([p for p in self.data['patients'] if p.get('agent_id')]),
            'total_alerts': len(self.data.get('alerts', [])),
            'high_priority_alerts': len([a for a in self.data.get('alerts', []) if a.get('priority') == 'high']),
            'total_instructions': len(self.data.get('nurse_instructions', []))
        }