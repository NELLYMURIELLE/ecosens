VUE D'ENSEMBLE DU PROJET

EcoSense est une application web de gestion et d'analyse de la consommation energetique.

Elle permet aux utilisateurs de:

Enregistrer leurs équipements électriques
Suivre leurs utilisations quotidiennes
Visualiser des statistiques avec des graphiques
Obtenir des prédictions de consommation future via Machine Learning
Comparer leur consommation mois par mois

Architecture du projet

Structure des dossiers 

EcoSense/
├── app.py                      # Application Flask principale 
├── database.db                 # Base de données SQLite
├── create_admin.py             # Script pour créer le super administrateur
├── migrate_alerts.py           # Script de migration de la base de données
│
├── models/
│   └── database.py             # Modèles de données (tables de la base)
│
├── utils/
│   └── calculations.py         # Fonctions de calculs et Machine Learning
│
├── templates/                  # Pages HTML (interface utilisateur)
│   ├── login.html
│   ├── register.html
│   ├── home.html
│   ├── equipments.html
│   ├── add_equipment.html
│   ├── edit_equipment.html
│   ├── add_usage.html
│   ├── edit_usage.html
│   ├── statistics.html
│   ├── predictions.html
│   ├── comparisons.html
│   ├── profile.html
│   ├── admin_panel.html
│   └── settings.html
│
└── static/
    └── css/
        └── style.css           # Styles CSS de l'application

 Bibliothèques utilisées et leurs rôles
 
1. Flask (flask)
Rôle : Framework web Python qui gère l'application web

Flask : Classe principale pour créer l'application
render_template() : Affiche les pages HTML en passant des données
request : Permet de récupérer les données envoyées par l'utilisateur (formulaires)
redirect() : Redirige vers une autre page
url_for() : Génère l'URL d'une route (évite de coder en dur les URLs)
session : Stocke les informations de l'utilisateur connecté (comme un panier)
flash() : Affiche des messages temporaires (succès, erreur, etc.)

2. SQLAlchemy (sqlalchemy)
Rôle : ORM (Object-Relational Mapping) - Permet de manipuler la base de données avec du code Python au lieu de SQL

create_engine() : Crée la connexion à la base de données
Column : Définit une colonne dans une table
Integer, String, Float, DateTime : Types de données
ForeignKey : Crée une relation entre deux tables
relationship() : Définit les liens entre les objets (un utilisateur a plusieurs équipements)
sessionmaker() : Crée des sessions pour interroger la base de données

3. Datetime (datetime)
Rôle : Gestion des dates et heures

datetime.now() : Date et heure actuelles
timedelta(days=7) : Durée (7 jours)
strftime('%d/%m/%Y') : Formate une date (ex: "06/01/2026")

4. Functools (functools)
Rôle : Outils pour les fonctions Python

5. NumPy (numpy)
Rôle : Bibliothèque de calcul scientifique (tableaux et opérations mathématiques)

np.array() : Crée un tableau de nombres
reshape(-1, 1) : Transforme le tableau pour le Machine Learning

6. Scikit-learn (sklearn)
Rôle : Machine Learning - Prédictions basées sur les données

LinearRegression() : Modèle de régression linéaire (trouve une tendance dans les données)
model.fit(X, y) : Entraîne le modèle avec les données passées
model.predict(X) : Prédit les valeurs futures
