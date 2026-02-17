from emergentintegrations.llm.chat import LlmChat, UserMessage
from dotenv import load_dotenv
import os
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = os.getenv("EMERGENT_LLM_KEY", "sk-emergent-753468924163d5fC03")
        self.model_provider = os.getenv("LLM_PROVIDER", "openai")
        self.model_name = os.getenv("LLM_MODEL", "gpt-4o")
    
    async def generate_report(self, case_data: dict) -> str:
        """Générer un rapport avec GPT-4o"""
        try:
            # Construire le contexte
            context = self._build_context(case_data)
            
            # Initialiser le chat LLM
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"report-{case_data.get('case_id', 'unknown')}",
                system_message="Vous êtes un assistant médical expert en anatomopathologie. Générez des rapports médicaux précis et détaillés."
            ).with_model(self.model_provider, self.model_name)
            
            # Créer le message utilisateur
            user_message = UserMessage(text=context)
            
            # Envoyer et obtenir la réponse
            response = await chat.send_message(user_message)
            
            logger.info(f"Report generated for case {case_data.get('case_id')}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating report with AI: {e}")
            return f"Erreur lors de la génération du rapport: {str(e)}"
    
    def _build_context(self, case_data: dict) -> str:
        """Construire le contexte pour le LLM"""
        context_parts = []
        
        # Instruction
        instruction = case_data.get('instruction', 'Génère un rapport médical détaillé')
        context_parts.append(f"### Instruction\n{instruction}\n")
        
        # Contexte patient
        if case_data.get('patient_context'):
            context_parts.append(f"### Contexte Patient\n{case_data['patient_context']}\n")
        
        # Annotations
        if case_data.get('annotations'):
            context_parts.append("### Annotations")
            for i, ann in enumerate(case_data['annotations'], 1):
                context_parts.append(f"{i}. {ann.get('label', 'Sans label')}: {ann.get('notes', '')}")
            context_parts.append("")
        
        # Rapports précédents
        if case_data.get('previous_reports'):
            context_parts.append("### Rapports Précédents")
            for i, report in enumerate(case_data['previous_reports'], 1):
                context_parts.append(f"\n**Rapport {i}**\n{report.get('content', '')}")
            context_parts.append("")
        
        context_parts.append("### Votre Rapport\nGénérez maintenant un rapport synthétique et professionnel:")
        
        return "\n".join(context_parts)
    
    async def analyze_image_annotations(self, image_base64: str, instruction: str) -> dict:
        """Analyser une image avec GPT-4o Vision"""
        try:
            from emergentintegrations.llm.chat import ImageContent
            
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"image-analysis-{os.urandom(4).hex()}",
                system_message="Vous êtes un expert en analyse d'images médicales. Détectez les anomalies et fournissez des annotations précises."
            ).with_model(self.model_provider, self.model_name)
            
            image_content = ImageContent(image_base64=image_base64)
            user_message = UserMessage(
                text=instruction,
                file_contents=[image_content]
            )
            
            response = await chat.send_message(user_message)
            
            return {
                "success": True,
                "analysis": response,
                "suggested_annotations": []  # Parser la réponse si nécessaire
            }
            
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {
                "success": False,
                "error": str(e)
            }
