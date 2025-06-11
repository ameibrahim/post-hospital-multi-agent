"""
Email Service Module - Handles all email functionality for the healthcare system
"""

from __future__ import print_function
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from google import genai

class EmailService:
    def __init__(self):
        """Initialize the email service with Brevo API configuration"""
        try:
            # Configure Brevo API
            self.configuration = sib_api_v3_sdk.Configuration()
            self.configuration.api_key['api-key'] = os.getenv('BREVO_API_KEY')
            
            # Create API instance
            self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(self.configuration)
            )
            
            # Configure Gemini AI for medical summaries (NEW FORMAT)
            gemini_api_key = os.getenv('GEMINI_API_KEY')
            if gemini_api_key:
                self.gemini_client = genai.Client(api_key=gemini_api_key)
            else:
                self.gemini_client = None
            
            # Email configuration
            self.sender_email = os.getenv('SENDER_EMAIL', 'noreply@yourhospital.com')
            self.sender_name = os.getenv('SENDER_NAME', 'Healthcare Team')
            self.hospital_name = os.getenv('HOSPITAL_NAME', 'General Hospital')
            
            print("✅ Email service initialized successfully")
            
        except Exception as e:
            print(f"❌ Error initializing email service: {e}")
            self.api_instance = None
            self.gemini_client = None

    def generate_medical_summary(self, patient_data):
        """Generate a personalized medical summary using Gemini AI"""
        try:
            if not self.gemini_client:
                return self._get_fallback_summary(patient_data)
                
            prompt = f"""
            Create a warm, personalized medical summary email for a patient who just received access to their post-hospital care system.

            Hospital Information:
            - Hospital Name: {self.hospital_name}
            - Care Team: The {self.hospital_name} Care Team

            Patient Information:
            - Name: {patient_data['name']}
            - Conditions: {', '.join(patient_data.get('conditions', [])) or 'None listed'}
            - Medications: {', '.join([f"{med['name']} ({med['dosage']} {med['frequency']})" for med in patient_data.get('medications', [])]) or 'None prescribed'}
            - Allergies: {', '.join(patient_data.get('allergies', [])) or 'None known'}
            - Discharge Plan: {patient_data.get('discharge_plan', 'Standard follow-up care')}

            Generate a caring, professional medical summary that:
            1. Welcomes the patient warmly on behalf of {self.hospital_name}
            2. Summarizes their current health status and care plan
            3. Explains how to use their healthcare assistant (Prof.Dux)
            4. Provides encouragement for their recovery journey
            5. Is written in simple, easy-to-understand language
            6. Signs off as "The {self.hospital_name} Care Team"

            Keep it personal but professional, around 100-200 words.
            """
            
            # Use the new Gemini API format
            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt
            )
            return response.text.strip()
            
        except Exception as e:
            print(f"❌ Error generating medical summary: {e}")
            return self._get_fallback_summary(patient_data)

    def _get_fallback_summary(self, patient_data):
        """Fallback medical summary when AI is unavailable"""
        return f"""
        Dear {patient_data['name']},

        Welcome to your personal post-hospital care system from {self.hospital_name}! We're here to support your recovery journey every step of the way.

        Your healthcare team has set up a personalized AI assistant called Prof.Dux to help you with questions about your medications, symptoms, and recovery. Your assistant knows about your medical history and can provide guidance 24/7.

        Your current care plan includes monitoring your health conditions and following your prescribed medication schedule. Prof.Dux will help you stay on track and answer any questions you might have about your recovery.

        Please use the login credentials provided to access your healthcare portal. If you have any concerning symptoms or urgent questions, don't hesitate to reach out to your healthcare team immediately.

        We're committed to supporting your recovery and helping you feel confident about managing your health at home.

        Wishing you a smooth and speedy recovery!

        The {self.hospital_name} Care Team
        """

    def create_welcome_email_content(self, patient_data, password, magic_token, magic_link):
        """Create the HTML content for the welcome email"""
        
        # Generate medical summary
        medical_summary = self.generate_medical_summary(patient_data)
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa;">
                
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #8B1538 0%, #A91E47 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
                    <h1 style="margin: 0; font-size: 28px; font-weight: bold;">🏥 Welcome to Your Healthcare Portal</h1>
                    <p style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.95;">{self.hospital_name} - Post-Hospital Care System</p>
                </div>
                
                <!-- Medical Summary Section -->
                <div style="background: white; padding: 25px; border-radius: 8px; margin-bottom: 25px; border-left: 4px solid #8B1538;">
                    <h2 style="color: #8B1538; margin-top: 0; font-size: 20px;">📋 Your Personalized Medical Summary</h2>
                    <div style="line-height: 1.8; color: #555;">{medical_summary}</div>
                </div>
                
                <!-- Login Credentials Section -->
                <div style="background: white; border: 2px solid #2c5aa0; padding: 25px; border-radius: 8px; margin-bottom: 25px;">
                    <h2 style="color: #2c5aa0; margin-top: 0; font-size: 20px;">🔐 Your Login Credentials</h2>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; color: #2c5aa0;">Patient ID:</td>
                            <td style="padding: 8px 0;">{patient_data['patient_id']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; color: #2c5aa0;">Password:</td>
                            <td style="padding: 8px 0;"><code style="background: #f8f9fa; padding: 5px 8px; border-radius: 4px; font-family: monospace; color: #d63384;">{password}</code></td>
                        </tr>
                    </table>
                    
                    <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px; font-size: 18px;">🪄 Quick Access Magic Link</h3>
                    <p style="margin-bottom: 20px; color: #666;">For easy access, click the button below (valid for 7 days):</p>
                    <div style="text-align: center; margin: 20px 0;">
                        <a href="{magic_link}" style="background: linear-gradient(135deg, #8B1538 0%, #A91E47 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block; box-shadow: 0 4px 8px rgba(139, 21, 56, 0.3);">🔗 Access Your Healthcare Portal</a>
                    </div>
                    <p style="font-size: 14px; color: #666; text-align: center;"><strong>Magic Token:</strong> <code style="background: #f8f9fa; padding: 5px 8px; border-radius: 4px; font-family: monospace; color: #6c757d;">{magic_token}</code></p>
                </div>
                
                <!-- Prof.Dux Introduction -->
                <div style="background: white; border: 2px solid #28a745; padding: 25px; border-radius: 8px; margin-bottom: 25px;">
                    <h3 style="color: #155724; margin-top: 0; font-size: 20px;">🤖 Meet Prof.Dux - Your AI Healthcare Assistant</h3>
                    <p style="margin-bottom: 15px; color: #155724;">Prof.Dux is your personal healthcare AI who knows about your medical history and can help with:</p>
                    <ul style="margin: 15px 0; padding-left: 20px; color: #155724;">
                        <li style="margin-bottom: 8px;">💊 Medication questions and scheduling</li>
                        <li style="margin-bottom: 8px;">🏥 Post-discharge care instructions</li>
                        <li style="margin-bottom: 8px;">⚠️ When to contact your healthcare team</li>
                        <li style="margin-bottom: 8px;">🩺 General health guidance and support</li>
                        <li style="margin-bottom: 8px;">❓ Answering your health-related questions</li>
                    </ul>
                </div>
                
                <!-- Medical Information Summary -->
                <div style="background: white; border: 2px solid #ffc107; padding: 25px; border-radius: 8px; margin-bottom: 25px;">
                    <h3 style="color: #856404; margin-top: 0; font-size: 20px;">📝 Important Medical Information</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; font-weight: bold; color: #856404; vertical-align: top; width: 30%;">Current Conditions:</td>
                            <td style="padding: 10px 0; color: #856404;">{', '.join(patient_data.get('conditions', [])) or 'None listed'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; font-weight: bold; color: #856404; vertical-align: top;">Current Medications:</td>
                            <td style="padding: 10px 0; color: #856404;">{self._format_medications_for_email(patient_data.get('medications', []))}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; font-weight: bold; color: #856404; vertical-align: top;">Known Allergies:</td>
                            <td style="padding: 10px 0; color: #856404;">{', '.join(patient_data.get('allergies', [])) or 'None known'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; font-weight: bold; color: #856404; vertical-align: top;">Discharge Plan:</td>
                            <td style="padding: 10px 0; color: #856404;">{patient_data.get('discharge_plan', 'Standard follow-up care')}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- Support Information -->
                <div style="background: white; padding: 25px; border-radius: 8px; text-align: center; border-top: 3px solid #8B1538;">
                    <h3 style="color: #8B1538; margin-top: 0;">📞 Need Help?</h3>
                    <p style="color: #666; margin-bottom: 10px;">If you have any questions or need assistance accessing your portal:</p>
                    <ul style="list-style: none; padding: 0; margin: 15px 0; color: #666;">
                        <li style="margin-bottom: 5px;">📧 Contact your {self.hospital_name} healthcare team</li>
                        <li style="margin-bottom: 5px;">🔗 Use the magic link for easy access</li>
                        <li style="margin-bottom: 5px;">💬 Chat with Prof.Dux for health questions</li>
                    </ul>
                    <p style="color: #8B1538; font-weight: bold; margin: 20px 0 0 0; font-size: 18px;">Wishing you a speedy recovery! 🌟</p>
                </div>
                
                <!-- Footer -->
                <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                    <p style="margin: 0;">This is an automated message from {self.hospital_name}.</p>
                    <p style="margin: 5px 0 0 0;">Please do not reply to this email.</p>
                </div>
                
            </div>
        </body>
        </html>
        """
        
        return html_content

    def _format_medications_for_email(self, medications):
        """Format medications list for email display"""
        if not medications:
            return 'None prescribed'
        
        formatted_meds = []
        for med in medications:
            formatted_meds.append(f"• {med['name']}: {med['dosage']} {med['frequency']}")
        
        return '<br>'.join(formatted_meds)

    def send_patient_credentials_email(self, patient_data, password, magic_token, request_host_url):
        """Send patient credentials and medical summary via Brevo API"""
        try:
            if not self.api_instance:
                print("❌ Email service not properly initialized")
                return False
            
            # Create magic link
            magic_link = f"{request_host_url}magic-login?token={magic_token}"
            
            # Create email content
            html_content = self.create_welcome_email_content(
                patient_data, password, magic_token, magic_link
            )
            
            # Prepare email subject
            email_subject = f"Welcome to Your Healthcare Portal - {patient_data['name']}"
            
            # Create email object using latest Brevo API structure
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                sender=sib_api_v3_sdk.SendSmtpEmailSender(
                    name=self.sender_name,
                    email=self.sender_email
                ),
                to=[sib_api_v3_sdk.SendSmtpEmailTo(
                    email=patient_data['email'],
                    name=patient_data['name']
                )],
                subject=email_subject,
                html_content=html_content,
                headers={
                    "charset": "utf-8",
                    "X-Priority": "1",
                    "X-MSMail-Priority": "High"
                }
            )
            
            # Send email using the transactional API
            api_response = self.api_instance.send_transac_email(send_smtp_email)
            
            print(f"✅ Email sent successfully to {patient_data['name']} ({patient_data['email']})")
            print(f"✅ Message ID: {api_response.message_id}")
            
            return True
            
        except ApiException as e:
            print(f"❌ Brevo API error: {e}")
            print(f"❌ Error body: {e.body if hasattr(e, 'body') else 'No error body'}")
            return False
        except Exception as e:
            print(f"❌ Email sending error: {e}")
            return False

    def send_simple_notification(self, to_email, to_name, subject, message):
        """Send a simple notification email"""
        try:
            if not self.api_instance:
                return False
            
            simple_html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: #8B1538; color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
                        <h1 style="margin: 0;">Healthcare Notification</h1>
                    </div>
                    <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #ddd;">
                        <p>{message}</p>
                    </div>
                    <div style="text-align: center; padding: 15px; color: #666; font-size: 12px;">
                        <p>This is an automated message from your healthcare system.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                sender=sib_api_v3_sdk.SendSmtpEmailSender(
                    name=self.sender_name,
                    email=self.sender_email
                ),
                to=[sib_api_v3_sdk.SendSmtpEmailTo(
                    email=to_email,
                    name=to_name
                )],
                subject=subject,
                html_content=simple_html
            )
            
            api_response = self.api_instance.send_transac_email(send_smtp_email)
            print(f"✅ Notification sent to {to_name} ({to_email})")
            return True
            
        except Exception as e:
            print(f"❌ Error sending notification: {e}")
            return False

# Create global email service instance
email_service = EmailService()