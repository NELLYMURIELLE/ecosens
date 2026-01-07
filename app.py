from flask import Flask, render_template, request, redirect, url_for, session, flash
from models.database import get_session, User, Equipment, Usage, Prediction
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete_super_securisee_123'


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vous devez être connecté.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


 # Redirection initiale
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))


# Inscription
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not email or not password:
            flash('Tous les champs sont obligatoires.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('register'))

        db = get_session()
        try:
            existing_user = db.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()

            if existing_user:
                flash('Nom d\'utilisateur ou email déjà utilisé.', 'danger')
                return redirect(url_for('register'))

            new_user = User(username=username, email=email)
            new_user.set_password(password)
            new_user.is_admin = 0  # Utilisateur normal
            new_user.is_approved = 0  # En attente de validation
            db.add(new_user)
            db.commit()

            flash('Inscription réussie ! En attente de validation par l\'administrateur.', 'info')
            return redirect(url_for('login'))
        finally:
            db.close()

    return render_template('register.html')


# Connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        db = get_session()
        try:
            user = db.query(User).filter(User.username == username).first()

            if user and user.check_password(password):
                # Vérifier si le compte est approuvé
                if user.is_approved == 0:
                    flash('Votre compte est en attente de validation par l\'administrateur.', 'warning')
                    return redirect(url_for('login'))

                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.is_admin
                flash(f'Bienvenue {user.username} !', 'success')
                return redirect(url_for('home'))
            else:
                flash('Identifiants incorrects.', 'danger')
        finally:
            db.close()

    return render_template('login.html')

# Route : Déconnexion
@app.route('/logout')
def logout():
    session.clear()
    flash('Déconnexion réussie.', 'info')
    return redirect(url_for('login'))


# Route : Accueil
@app.route('/home')
@login_required
def home():
    user_id = session['user_id']
    db = get_session()

    try:
        from utils.calculations import get_user_alerts

        # Récupérer l'utilisateur
        user = db.query(User).filter(User.id == user_id).first()

        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        usages_today = db.query(Usage).filter(
            Usage.user_id == user_id,
            Usage.date >= today_start,
            Usage.date <= today_end
        ).all()

        total_today = sum(usage.consommation_kwh for usage in usages_today)

        recent_usages = db.query(Usage).filter(
            Usage.user_id == user_id
        ).order_by(Usage.date.desc()).limit(5).all()

        total_equipments = db.query(Equipment).filter(
            Equipment.user_id == user_id
        ).count()

        # Récupérer les alertes
        alerts = get_user_alerts(user_id)

        # Récupérer l'objectif quotidien (avec valeur par défaut si None)
        daily_goal = user.daily_goal if user.daily_goal else 5.0

        return render_template('home.html',
                               total_today=round(total_today, 2),
                               recent_usages=recent_usages,
                               total_equipments=total_equipments,
                               alerts=alerts,
                               daily_goal=daily_goal)
    finally:
        db.close()

# Liste des équipements
@app.route('/equipments')
@login_required
def equipments():
    user_id = session['user_id']
    db = get_session()

    try:
        equipments_list = db.query(Equipment).filter(
            Equipment.user_id == user_id
        ).all()

        return render_template('equipments.html', equipments=equipments_list)
    finally:
        db.close()


# Ajouter un équipement
@app.route('/add_equipment', methods=['GET', 'POST'])
@login_required
def add_equipment():
    if request.method == 'POST':
        name = request.form.get('name')
        puissance = request.form.get('puissance')
        category = request.form.get('category')

        if not name or not puissance or not category:
            flash('Tous les champs sont obligatoires.', 'danger')
            return redirect(url_for('add_equipment'))

        db = get_session()
        try:
            new_equipment = Equipment(
                user_id=session['user_id'],
                name=name,
                puissance_watts=float(puissance),
                category=category
            )
            db.add(new_equipment)
            db.commit()

            flash(f'Équipement "{name}" ajouté !', 'success')
            return redirect(url_for('equipments'))
        finally:
            db.close()

    return render_template('add_equipment.html')


# Enregistrer une utilisation
@app.route('/add_usage', methods=['GET', 'POST'])
@login_required
def add_usage():
    user_id = session['user_id']
    db = get_session()

    try:
        if request.method == 'POST':
            equipment_id = request.form.get('equipment_id')
            heures = request.form.get('heures', 0)
            minutes = request.form.get('minutes', 0)
            consommation_manuelle = request.form.get('consommation_kwh')
            date_str = request.form.get('date')

            if not equipment_id:
                flash('Sélectionnez un équipement.', 'danger')
                return redirect(url_for('add_usage'))

            equipment = db.query(Equipment).filter(
                Equipment.id == equipment_id,
                Equipment.user_id == user_id
            ).first()

            if not equipment:
                flash('Équipement introuvable.', 'danger')
                return redirect(url_for('add_usage'))

            duree_heures = float(heures) + (float(minutes) / 60)

            if consommation_manuelle and float(consommation_manuelle) > 0:
                consommation = float(consommation_manuelle)
            else:
                consommation = (equipment.puissance_watts * duree_heures) / 1000

            usage_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M') if date_str else datetime.now()

            new_usage = Usage(
                user_id=user_id,
                equipment_id=equipment_id,
                date=usage_date,
                duree_heures=duree_heures,
                consommation_kwh=consommation
            )

            db.add(new_usage)
            db.commit()

            # Vérifier les alertes de surconsommation
            from utils.calculations import check_daily_consumption_alert
            check_daily_consumption_alert(user_id)

            flash(f'Enregistré : {round(consommation, 2)} kWh', 'success')
            return redirect(url_for('home'))

        equipments_list = db.query(Equipment).filter(
            Equipment.user_id == user_id
        ).all()

        return render_template('add_usage.html', equipments=equipments_list)
    finally:
        db.close()


# Statistiques
@app.route('/statistics')
@login_required
def statistics():
    user_id = session['user_id']
    db = get_session()

    try:
        from utils.calculations import (
            get_weekly_data,
            get_monthly_data,
            get_equipment_breakdown
        )

        # Statistiques globales
        total_usages = db.query(Usage).filter(Usage.user_id == user_id).count()
        total_kwh = db.query(Usage).filter(Usage.user_id == user_id).all()
        total_consommation = sum(u.consommation_kwh for u in total_kwh)

        # Cette semaine
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_usages = db.query(Usage).filter(
            Usage.user_id == user_id,
            Usage.date >= week_start
        ).all()
        week_total = sum(u.consommation_kwh for u in week_usages)

        # Ce mois
        month_start = today.replace(day=1)
        month_usages = db.query(Usage).filter(
            Usage.user_id == user_id,
            Usage.date >= month_start
        ).all()
        month_total = sum(u.consommation_kwh for u in month_usages)

        # Données pour graphiques
        weekly_data = get_weekly_data(user_id)
        monthly_data = get_monthly_data(user_id)
        equipment_data = get_equipment_breakdown(user_id)

        return render_template('statistics.html',
                               total_usages=total_usages,
                               total_consommation=round(total_consommation, 2),
                               week_total=round(week_total, 2),
                               month_total=round(month_total, 2),
                               weekly_data=weekly_data,
                               monthly_data=monthly_data,
                               equipment_data=equipment_data)
    finally:
        db.close()

# Supprimer un équipement
@app.route('/delete_equipment/<int:equipment_id>')
@login_required
def delete_equipment(equipment_id):
    user_id = session['user_id']
    db = get_session()

    try:
        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.user_id == user_id
        ).first()

        if equipment:
            db.delete(equipment)
            db.commit()
            flash(f'Équipement "{equipment.name}" supprimé.', 'success')
        else:
            flash('Équipement introuvable.', 'danger')
    finally:
        db.close()

    return redirect(url_for('equipments'))


# Modifier un équipement
@app.route('/edit_equipment/<int:equipment_id>', methods=['GET', 'POST'])
@login_required
def edit_equipment(equipment_id):
    user_id = session['user_id']
    db = get_session()

    try:
        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.user_id == user_id
        ).first()

        if not equipment:
            flash('Équipement introuvable.', 'danger')
            return redirect(url_for('equipments'))

        if request.method == 'POST':
            equipment.name = request.form.get('name')
            equipment.puissance_watts = float(request.form.get('puissance'))
            equipment.category = request.form.get('category')
            db.commit()

            flash(f'Équipement "{equipment.name}" modifié.', 'success')
            return redirect(url_for('equipments'))

        return render_template('edit_equipment.html', equipment=equipment)
    finally:
        db.close()


# Supprimer une utilisation
@app.route('/delete_usage/<int:usage_id>')
@login_required
def delete_usage(usage_id):
    user_id = session['user_id']
    db = get_session()

    try:
        usage = db.query(Usage).filter(
            Usage.id == usage_id,
            Usage.user_id == user_id
        ).first()

        if usage:
            db.delete(usage)
            db.commit()
            flash('Utilisation supprimée.', 'success')
        else:
            flash('Utilisation introuvable.', 'danger')
    finally:
        db.close()

    return redirect(url_for('home'))


# Modifier une utilisation
@app.route('/edit_usage/<int:usage_id>', methods=['GET', 'POST'])
@login_required
def edit_usage(usage_id):
    user_id = session['user_id']
    db = get_session()

    try:
        usage = db.query(Usage).filter(
            Usage.id == usage_id,
            Usage.user_id == user_id
        ).first()

        if not usage:
            flash('Utilisation introuvable.', 'danger')
            return redirect(url_for('home'))

        if request.method == 'POST':
            heures = float(request.form.get('heures', 0))
            minutes = float(request.form.get('minutes', 0))
            usage.duree_heures = heures + (minutes / 60)
            usage.consommation_kwh = float(request.form.get('consommation_kwh'))
            usage.date = datetime.strptime(request.form.get('date'), '%Y-%m-%dT%H:%M')
            db.commit()

            flash('Utilisation modifiée.', 'success')
            return redirect(url_for('home'))

        equipments_list = db.query(Equipment).filter(
            Equipment.user_id == user_id
        ).all()

        return render_template('edit_usage.html', usage=usage, equipments=equipments_list)
    finally:
        db.close()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vous devez être connecté.', 'warning')
            return redirect(url_for('login'))
        if session.get('is_admin') != 1:
            flash('Accès refusé : réservé aux administrateurs.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)

    return decorated_function


# Panel d'administration
@app.route('/admin')
@admin_required
def admin_panel():
    db = get_session()

    try:
        # Utilisateurs en attente de validation
        pending_users = db.query(User).filter(User.is_approved == 0).all()

        # Tous les utilisateurs approuvés
        approved_users = db.query(User).filter(User.is_approved == 1).all()

        return render_template('admin_panel.html',
                               pending_users=pending_users,
                               approved_users=approved_users)
    finally:
        db.close()


# Approuver un utilisateur
@app.route('/admin/approve/<int:user_id>')
@admin_required
def approve_user(user_id):
    db = get_session()

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if user:
            user.is_approved = 1
            db.commit()
            flash(f'Utilisateur "{user.username}" approuvé !', 'success')
        else:
            flash('Utilisateur introuvable.', 'danger')
    finally:
        db.close()

    return redirect(url_for('admin_panel'))


# Rejeter un utilisateur
@app.route('/admin/reject/<int:user_id>')
@admin_required
def reject_user(user_id):
    db = get_session()

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if user:
            db.delete(user)
            db.commit()
            flash(f'Utilisateur "{user.username}" rejeté et supprimé.', 'success')
        else:
            flash('Utilisateur introuvable.', 'danger')
    finally:
        db.close()

    return redirect(url_for('admin_panel'))


# Supprimer un utilisateur approuvé
@app.route('/admin/delete/<int:user_id>')
@admin_required
def delete_user(user_id):
    db = get_session()

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if user and user.id != session['user_id']:  # Ne peut pas se supprimer lui-même
            db.delete(user)
            db.commit()
            flash(f'Utilisateur "{user.username}" supprimé.', 'success')
        else:
            flash('Impossible de supprimer cet utilisateur.', 'danger')
    finally:
        db.close()

    return redirect(url_for('admin_panel'))


# Profil utilisateur
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    db = get_session()

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if request.method == 'POST':
            action = request.form.get('action')

            # Modifier le nom d'utilisateur et email
            if action == 'update_info':
                new_username = request.form.get('username')
                new_email = request.form.get('email')

                # Vérifier si le nom d'utilisateur ou email existe déjà
                existing = db.query(User).filter(
                    User.id != user_id,
                    (User.username == new_username) | (User.email == new_email)
                ).first()

                if existing:
                    flash('Ce nom d\'utilisateur ou email est déjà utilisé.', 'danger')
                else:
                    user.username = new_username
                    user.email = new_email
                    session['username'] = new_username
                    db.commit()
                    flash('Informations mises à jour !', 'success')

            # Changer le mot de passe
            elif action == 'change_password':
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')

                if not user.check_password(current_password):
                    flash('Mot de passe actuel incorrect.', 'danger')
                elif new_password != confirm_password:
                    flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
                elif len(new_password) < 4:
                    flash('Le mot de passe doit contenir au moins 4 caractères.', 'warning')
                else:
                    user.set_password(new_password)
                    db.commit()
                    flash('Mot de passe changé avec succès !', 'success')

        return render_template('profile.html', user=user)
    finally:
        db.close()


# Prédictions
@app.route('/predictions')
@login_required
def predictions():
    user_id = session['user_id']

    from utils.calculations import predict_next_week

    predictions_data = predict_next_week(user_id)

    if predictions_data is None:
        flash('Pas assez de données pour faire des prédictions (minimum 7 jours).', 'warning')

    return render_template('predictions.html', predictions=predictions_data)


# Marquer alerte comme lue
@app.route('/alert/read/<int:alert_id>')
@login_required
def mark_alert_read(alert_id):
    from utils.calculations import mark_alert_as_read
    mark_alert_as_read(alert_id)
    return redirect(url_for('home'))


# Paramètres d'alerte
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user_id = session['user_id']
    db = get_session()

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if request.method == 'POST':
            user.alert_threshold = float(request.form.get('alert_threshold', 10))
            user.daily_goal = float(request.form.get('daily_goal', 5))
            db.commit()
            flash('Paramètres enregistrés !', 'success')
            return redirect(url_for('settings'))

        return render_template('settings.html', user=user)
    finally:
        db.close()


# Comparaisons mensuelles
@app.route('/comparisons')
@login_required
def comparisons():
    user_id = session['user_id']

    from utils.calculations import get_monthly_comparison, get_comparison_stats

    monthly_data = get_monthly_comparison(user_id, months=6)
    comparison_stats = get_comparison_stats(user_id)

    return render_template('comparisons.html',
                           monthly_data=monthly_data,
                           stats=comparison_stats)

if __name__ == '__main__':
    app.run(debug=True)