"""
Script pour remplir la base de données avec des données de test
"""

import asyncio
from datetime import datetime, timedelta
from database import init_db, create_conversation, add_message

# Données de test pour les conversations
CONVERSATION_TITLES = [
    "Réunion avec le client espagnol",
    "Discussion technique sur le projet",
    "Entretien d'embauche",
    "Présentation produit",
    "Formation équipe",
    "Appel support client",
    "Réunion stratégique",
    "Brainstorming créatif",
]

# Messages de test (français -> espagnol)
MESSAGES_DATA = [
    # Conversation 1 - Réunion client
    [
        ("Bonjour, comment allez-vous aujourd'hui ?", "Hola, ¿cómo está hoy?", "fr"),
        ("Très bien, merci. Et vous ?", "Muy bien, gracias. ¿Y usted?", "fr"),
        ("Parfait. Commençons la réunion.", "Perfecto. Empecemos la reunión.", "fr"),
        (
            "D'accord, j'ai préparé quelques points à discuter.",
            "De acuerdo, he preparado algunos puntos para discutir.",
            "fr",
        ),
    ],
    # Conversation 2 - Discussion technique
    [
        ("Quel est le statut du projet ?", "¿Cuál es el estado del proyecto?", "fr"),
        (
            "Nous avons terminé 80% du développement.",
            "Hemos completado el 80% del desarrollo.",
            "fr",
        ),
        ("Excellent travail !", "¡Excelente trabajo!", "fr"),
        (
            "Merci, nous prévoyons de terminer la semaine prochaine.",
            "Gracias, planeamos terminar la próxima semana.",
            "fr",
        ),
    ],
    # Conversation 3 - Entretien
    [
        (
            "Bonjour, racontez-moi votre parcours professionnel.",
            "Hola, cuénteme sobre su trayectoria profesional.",
            "fr",
        ),
        (
            "J'ai travaillé dans le développement logiciel pendant 5 ans.",
            "He trabajado en desarrollo de software durante 5 años.",
            "fr",
        ),
        (
            "Quelles sont vos compétences principales ?",
            "¿Cuáles son sus principales habilidades?",
            "fr",
        ),
        (
            "Python, JavaScript et gestion de projets.",
            "Python, JavaScript y gestión de proyectos.",
            "fr",
        ),
    ],
    # Conversation 4 - Présentation
    [
        (
            "Aujourd'hui, je vais vous présenter notre nouveau produit.",
            "Hoy, les presentaré nuestro nuevo producto.",
            "fr",
        ),
        (
            "Quelles sont ses fonctionnalités principales ?",
            "¿Cuáles son sus principales funcionalidades?",
            "fr",
        ),
        (
            "Il inclut la traduction en temps réel et l'analyse vocale.",
            "Incluye traducción en tiempo real y análisis de voz.",
            "fr",
        ),
        (
            "Impressionnant ! Quand sera-t-il disponible ?",
            "¡Impresionante! ¿Cuándo estará disponible?",
            "fr",
        ),
    ],
    # Conversation 5 - Formation
    [
        (
            "Bienvenue à la formation d'aujourd'hui.",
            "Bienvenidos a la formación de hoy.",
            "fr",
        ),
        (
            "Nous allons apprendre à utiliser le nouveau système.",
            "Vamos a aprender a usar el nuevo sistema.",
            "fr",
        ),
        ("Avez-vous des questions ?", "¿Tienen alguna pregunta?", "fr"),
        (
            "Oui, comment configurer les paramètres ?",
            "Sí, ¿cómo configurar los parámetros?",
            "fr",
        ),
    ],
    # Conversation 6 - Support
    [
        (
            "Bonjour, j'ai un problème avec mon compte.",
            "Hola, tengo un problema con mi cuenta.",
            "fr",
        ),
        ("Pouvez-vous me donner plus de détails ?", "¿Puede darme más detalles?", "fr"),
        (
            "Je ne peux pas me connecter depuis hier.",
            "No puedo iniciar sesión desde ayer.",
            "fr",
        ),
        (
            "Je vais vérifier cela immédiatement.",
            "Voy a verificar esto de inmediato.",
            "fr",
        ),
    ],
    # Conversation 7 - Stratégie
    [
        (
            "Quels sont nos objectifs pour le trimestre ?",
            "¿Cuáles son nuestros objetivos para el trimestre?",
            "fr",
        ),
        (
            "Nous visons une croissance de 20%.",
            "Apuntamos a un crecimiento del 20%.",
            "fr",
        ),
        ("Comment allons-nous y parvenir ?", "¿Cómo lo lograremos?", "fr"),
        (
            "En améliorant notre marketing et nos ventes.",
            "Mejorando nuestro marketing y ventas.",
            "fr",
        ),
    ],
    # Conversation 8 - Brainstorming
    [
        (
            "Avez-vous des idées pour le nouveau logo ?",
            "¿Tienen ideas para el nuevo logo?",
            "fr",
        ),
        (
            "Je pense qu'il devrait être moderne et coloré.",
            "Creo que debería ser moderno y colorido.",
            "fr",
        ),
        (
            "Et peut-être inclure notre mascotte ?",
            "¿Y tal vez incluir nuestra mascota?",
            "fr",
        ),
        ("Excellente idée !", "¡Excelente idea!", "fr"),
    ],
]


async def populate_database():
    """Remplit la base de données avec des données de test"""
    print("Initialisation de la base de données...")
    await init_db()
    print("✓ Base de données initialisée\n")

    conversations = []

    # Créer les conversations
    print("Création des conversations...")
    for i, title in enumerate(CONVERSATION_TITLES):
        conv = await create_conversation(title)
        conversations.append(conv)
        print(f"✓ Conversation créée: {title} (ID: {conv.id})")
    print()

    # Ajouter les messages à chaque conversation
    print("Ajout des messages...")
    base_time = datetime.now() - timedelta(days=7)  # Commencer il y a 7 jours

    for conv_idx, conv in enumerate(conversations):
        messages = MESSAGES_DATA[conv_idx] if conv_idx < len(MESSAGES_DATA) else []

        for msg_idx, (fr, es, source_lang) in enumerate(messages):
            # Créer un timestamp progressif pour chaque message
            timestamp = base_time + timedelta(
                days=conv_idx, hours=msg_idx * 2, minutes=msg_idx * 15
            )

            await add_message(
                conversation_id=conv.id,
                fr=fr,
                es=es,
                source_language=source_lang,
                timestamp=timestamp,
            )
            print(f"✓ Message ajouté à la conversation {conv.id}: {fr[:50]}...")

    print(f"\n✓ Base de données remplie avec succès !")
    print(f"  - {len(conversations)} conversations créées")
    total_messages = sum(len(msgs) for msgs in MESSAGES_DATA)
    print(f"  - {total_messages} messages créés")


if __name__ == "__main__":
    asyncio.run(populate_database())
