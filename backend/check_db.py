from database import SessionLocal, User, Medication, Role

db = SessionLocal()
med = db.query(Medication).filter(Medication.id == 1).first()

if med:
    patient = med.patient
    print(f"Medicijn: {med.name}")
    print(f"Patiënt: {patient.username}")
    
    # Check de koppeling
    caregiver = db.query(User).filter(User.id == patient.caregiver_id).first()
    if caregiver:
        print(f"Mantelzorger gevonden: {caregiver.username}")
        print(f"E-mail van mantelzorger: {caregiver.email}")
    else:
        print("FOUT: Geen mantelzorger gekoppeld aan deze patiënt! (caregiver_id is leeg)")
else:
    print("FOUT: Medicijn met ID 1 niet gevonden in de database.")
db.close()