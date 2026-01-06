from models.database import get_session, User

db = get_session()

# Vérifie si un admin existe déjà
existing_admin = db.query(User).filter(User.is_admin == 1).first()

if existing_admin:
    print(f"⚠️ Un admin existe déjà : {existing_admin.username}")
else:
    # Crée le super admin
    admin = User(
        username="Nel",
        email="nel@gmail.com"
    )
    admin.set_password("nel123321")
    admin.is_admin = 1
    admin.is_approved = 1

    db.add(admin)
    db.commit()
    print("✅ Super admin créé !")
    print("   Username: Nel")
    print("   Password: nel123321")
    print("   ⚠️ CHANGE CE MOT DE PASSE après connexion !")

db.close()