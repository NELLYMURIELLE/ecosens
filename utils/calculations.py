from datetime import datetime, timedelta
from models.database import get_session, Usage
import numpy as np
from sklearn.linear_model import LinearRegression


def get_weekly_data(user_id):
    """Récupère les données de la semaine"""
    db = get_session()
    try:
        today = datetime.now()
        week_ago = today - timedelta(days=7)

        usages = db.query(Usage).filter(
            Usage.user_id == user_id,
            Usage.date >= week_ago
        ).all()

        # Grouper par jour
        daily_data = {}
        for usage in usages:
            day = usage.date.strftime('%Y-%m-%d')
            if day not in daily_data:
                daily_data[day] = 0
            daily_data[day] += usage.consommation_kwh

        # Compléter les jours manquants avec 0
        result = []
        for i in range(7):
            date = (today - timedelta(days=6 - i)).strftime('%Y-%m-%d')
            result.append({
                'date': date,
                'day_name': (today - timedelta(days=6 - i)).strftime('%a'),
                'consommation': round(daily_data.get(date, 0), 2)
            })

        return result
    finally:
        db.close()


def get_monthly_data(user_id):
    """Récupère les données du mois"""
    db = get_session()
    try:
        today = datetime.now()
        month_start = today.replace(day=1)

        usages = db.query(Usage).filter(
            Usage.user_id == user_id,
            Usage.date >= month_start
        ).all()

        # Grouper par semaine
        weekly_data = {}
        for usage in usages:
            week_num = usage.date.isocalendar()[1]
            if week_num not in weekly_data:
                weekly_data[week_num] = 0
            weekly_data[week_num] += usage.consommation_kwh

        result = []
        for week_num, total in sorted(weekly_data.items()):
            result.append({
                'week': f'Semaine {week_num}',
                'consommation': round(total, 2)
            })

        return result
    finally:
        db.close()


def get_equipment_breakdown(user_id):
    """Répartition par équipement"""
    db = get_session()
    try:
        usages = db.query(Usage).filter(Usage.user_id == user_id).all()

        equipment_data = {}
        for usage in usages:
            name = usage.equipment.name
            if name not in equipment_data:
                equipment_data[name] = 0
            equipment_data[name] += usage.consommation_kwh

        # Trier par consommation décroissante
        sorted_data = sorted(equipment_data.items(), key=lambda x: x[1], reverse=True)

        result = []
        for name, total in sorted_data[:10]:  # Top 10
            result.append({
                'name': name,
                'consommation': round(total, 2)
            })

        return result
    finally:
        db.close()


def predict_next_week(user_id):
    """Prédiction pour la semaine prochaine avec régression linéaire"""
    db = get_session()
    try:
        # Récupérer les 30 derniers jours
        today = datetime.now()
        month_ago = today - timedelta(days=30)

        usages = db.query(Usage).filter(
            Usage.user_id == user_id,
            Usage.date >= month_ago
        ).all()

        if len(usages) < 7:
            return None  # Pas assez de données

        # Grouper par jour
        daily_data = {}
        for usage in usages:
            day = usage.date.strftime('%Y-%m-%d')
            if day not in daily_data:
                daily_data[day] = 0
            daily_data[day] += usage.consommation_kwh

        # Préparer les données pour la régression
        dates = sorted(daily_data.keys())
        X = np.array(range(len(dates))).reshape(-1, 1)
        y = np.array([daily_data[date] for date in dates])

        # Créer et entraîner le modèle
        model = LinearRegression()
        model.fit(X, y)

        # Prédire les 7 prochains jours
        future_X = np.array(range(len(dates), len(dates) + 7)).reshape(-1, 1)
        predictions = model.predict(future_X)

        result = []
        for i, pred in enumerate(predictions):
            future_date = today + timedelta(days=i + 1)
            result.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'day_name': future_date.strftime('%a'),
                'prediction': round(max(0, pred), 2)
            })

        return result
    finally:
        db.close()


def check_daily_consumption_alert(user_id):
    """Vérifie si la consommation du jour dépasse le seuil"""
    from models.database import User, Alert

    db = get_session()
    try:
        user = db.query(User).filter(User.id == user_id).first()

        # Consommation du jour
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        usages = db.query(Usage).filter(
            Usage.user_id == user_id,
            Usage.date >= today_start,
            Usage.date <= today_end
        ).all()

        daily_total = sum(u.consommation_kwh for u in usages)

        # Vérifier si dépasse le seuil
        if daily_total > user.alert_threshold:
            # Vérifier si une alerte similaire existe déjà aujourd'hui
            existing_alert = db.query(Alert).filter(
                Alert.user_id == user_id,
                Alert.alert_type == 'warning',
                Alert.date_created >= today_start
            ).first()

            if not existing_alert:
                alert = Alert(
                    user_id=user_id,
                    message=f"⚠️ Surconsommation détectée : {round(daily_total, 2)} kWh aujourd'hui (seuil : {user.alert_threshold} kWh)",
                    alert_type='warning'
                )
                db.add(alert)
                db.commit()
                return True

        return False
    finally:
        db.close()


def get_user_alerts(user_id):
    """Récupère les alertes non lues de l'utilisateur"""
    from models.database import Alert

    db = get_session()
    try:
        alerts = db.query(Alert).filter(
            Alert.user_id == user_id,
            Alert.is_read == 0
        ).order_by(Alert.date_created.desc()).limit(5).all()

        return alerts
    finally:
        db.close()


def mark_alert_as_read(alert_id):
    """Marquer une alerte comme lue"""
    from models.database import Alert

    db = get_session()
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.is_read = 1
            db.commit()
    finally:
        db.close()


def get_monthly_comparison(user_id, months=6):
    """Comparaison des N derniers mois"""
    db = get_session()
    try:
        today = datetime.now()
        result = []

        for i in range(months):
            # Calculer le mois
            month_date = today - timedelta(days=30 * i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Calculer le dernier jour du mois
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(seconds=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(seconds=1)

            # Récupérer les usages du mois
            usages = db.query(Usage).filter(
                Usage.user_id == user_id,
                Usage.date >= month_start,
                Usage.date <= month_end
            ).all()

            total = sum(u.consommation_kwh for u in usages)

            result.append({
                'month': month_start.strftime('%B %Y'),
                'month_short': month_start.strftime('%b %Y'),
                'consommation': round(total, 2),
                'cout': round(total * 150, 0)
            })

        # Inverser pour avoir du plus ancien au plus récent
        return list(reversed(result))
    finally:
        db.close()


def get_comparison_stats(user_id):
    """Statistiques de comparaison"""
    db = get_session()
    try:
        today = datetime.now()

        # Mois actuel
        current_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_usages = db.query(Usage).filter(
            Usage.user_id == user_id,
            Usage.date >= current_month_start
        ).all()
        current_month_total = sum(u.consommation_kwh for u in current_month_usages)

        # Mois précédent
        if current_month_start.month == 1:
            last_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
        else:
            last_month_start = current_month_start.replace(month=current_month_start.month - 1)

        last_month_usages = db.query(Usage).filter(
            Usage.user_id == user_id,
            Usage.date >= last_month_start,
            Usage.date < current_month_start
        ).all()
        last_month_total = sum(u.consommation_kwh for u in last_month_usages)

        # Calculer la différence
        if last_month_total > 0:
            difference = ((current_month_total - last_month_total) / last_month_total) * 100
        else:
            difference = 0

        # Moyenne mensuelle (6 derniers mois)
        six_months_ago = today - timedelta(days=180)
        all_usages = db.query(Usage).filter(
            Usage.user_id == user_id,
            Usage.date >= six_months_ago
        ).all()

        total_consumption = sum(u.consommation_kwh for u in all_usages)
        average_monthly = total_consumption / 6 if all_usages else 0

        return {
            'current_month': round(current_month_total, 2),
            'last_month': round(last_month_total, 2),
            'difference': round(difference, 1),
            'average_monthly': round(average_monthly, 2),
            'trend': 'up' if difference > 0 else 'down' if difference < 0 else 'stable'
        }
    finally:
        db.close()