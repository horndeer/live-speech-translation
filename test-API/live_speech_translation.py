import os
import time
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()

def start_wedding_translator():
    # 1. Configuration de base
    # Note: Il est souvent plus simple d'utiliser 'region' plutôt que 'endpoint'
    speech_key = os.environ.get('SPEECH_KEY')
    service_region = os.environ.get('SPEECH_REGION')

    if not speech_key or not service_region:
        print("❌ Erreur: Clés manquantes dans le fichier .env")
        return

    translation_config = speechsdk.translation.SpeechTranslationConfig(
        subscription=speech_key, 
        region=service_region
    )

    # 2. Configuration de la traduction
    # On ajoute les deux langues cibles.
    # Azure traduira vers les DEUX, nous afficherons celle qui nous intéresse.
    translation_config.add_target_language("fr")
    translation_config.add_target_language("es")

    # 3. Configuration de la détection automatique de langue (Source)
    # On précise à Azure de s'attendre soit à du Français (France), soit à de l'Espagnol (Mexique)
    auto_detect_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
        languages=["fr-FR", "es-MX"]
    )

    # 4. Configuration Audio
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

    # 5. Création du Recognizer
    recognizer = speechsdk.translation.TranslationRecognizer(
        translation_config=translation_config, 
        audio_config=audio_config,
        auto_detect_source_language_config=auto_detect_config
    )

    # --- GESTION DES ÉVÉNEMENTS (CALLBACKS) ---

    def result_callback(evt):
        """Appelé quand une phrase est TERMINÉE et TRADUITE"""
        if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
            
            # Détection de la langue parlée (ex: 'fr-FR' ou 'es-MX')
            detected_lang = evt.result.properties[speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult]
            
            print(f"\n🗣️  Langue détectée: {detected_lang}")
            print(f"Original: {evt.result.text}")

            # Logique d'affichage croisé
            if "fr" in detected_lang:
                # Si on parle français, on veut voir l'espagnol
                print(f"🇲🇽 Traduction: {evt.result.translations['es']}")
            elif "es" in detected_lang:
                # Si on parle espagnol, on veut voir le français
                print(f"🇫🇷 Traduction: {evt.result.translations['fr']}")
            
            print("-" * 30)

    def recognizing_callback(evt):
        """Appelé plusieurs fois par seconde pendant que la personne parle"""
        if evt.result.reason == speechsdk.ResultReason.TranslatingSpeech:
            
            # 1. Récupération de la langue détectée (peut être instable au tout début)
            auto_detect_source_language_result = evt.result.properties[speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult]
            
            # 2. Logique d'affichage croisé (identique à tout à l'heure)
            target_text = ""
            
            if "fr" in auto_detect_source_language_result:
                # L'orateur parle Français -> On prépare l'Espagnol
                target_text = evt.result.translations['es']
                prefix = "🇲🇽 (En cours...)"
                
            elif "es" in auto_detect_source_language_result:
                # L'orateur parle Espagnol -> On prépare le Français
                target_text = evt.result.translations['fr']
                prefix = "🇫🇷 (En cours...)"
            else:
                # Langue pas encore identifiée (les premières millisecondes)
                prefix = "⏳ (...)"
                target_text = "..."

            # 3. Affichage dynamique (On écrase la ligne actuelle)
            # \r ramène le curseur au début de la ligne sans sauter de ligne
            # ljust(100) ajoute des espaces vides pour effacer les traces de phrases précédentes plus longues
            print(f"\r{prefix} : {target_text}".ljust(100), end="", flush=True)

    # Connexion des événements
    recognizer.recognized.connect(result_callback)
    recognizer.recognizing.connect(recognizing_callback)

    # --- BOUCLE PRINCIPALE ---
    
    print("--------------------------------------------------")
    print("🎙️  WEDDING TRANSLATOR (FR <-> MX)")
    print("Appuyez sur Entrée pour DÉMARRER l'écoute.")
    print("Appuyez sur Ctrl+C pour QUITTER complètement.")
    print("--------------------------------------------------")

    try:
        input() # Attente utilisateur
        print("🔴 Écoute en cours... (Parlez maintenant)")
        
        # Démarrage de la reconnaissance continue
        recognizer.start_continuous_recognition()

        while True:
            # On utilise une boucle simple ici pour maintenir le script en vie
            # Dans une vraie app graphique, ce serait géré par la fenêtre
            user_input = input("Appuyez sur Entrée pour mettre en PAUSE ou 'q' pour quitter: ")
            
            if user_input.lower() == 'q':
                break
            
            print("⏸️  Pause... (Économie API)")
            recognizer.stop_continuous_recognition()
            
            input("Appuyez sur Entrée pour REPRENDRE...")
            print("🔴 Reprise de l'écoute...")
            recognizer.start_continuous_recognition()

    except KeyboardInterrupt:
        pass
    finally:
        recognizer.stop_continuous_recognition()
        print("\nArrêt du programme.")

if __name__ == "__main__":
    start_wedding_translator()